import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CheckCircle, Circle, Download, ExternalLink, Send, X } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import api from '../../api/axios';
import { onboardingAPI, regulationsAPI } from '../../api/content';

const STATUS_LABELS = {
  draft: 'Черновик',
  sent: 'Отправлен',
  accepted: 'Принят',
  rework: 'На доработке',
  rejected: 'Отклонен',
};

const normStatus = (value) => {
  const raw = String(value || '').toLowerCase();
  if (raw === 'draft') return 'draft';
  if (raw === 'sent') return 'sent';
  if (raw === 'accepted') return 'accepted';
  if (raw === 'revision' || raw === 'rework') return 'rework';
  if (raw === 'rejected') return 'rejected';
  return 'draft';
};

const toAbsoluteMedia = (url) => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  const origin = apiBase.replace(/\/api\/?$/, '');
  return `${origin}${url.startsWith('/') ? '' : '/'}${url}`;
};

const findReportByDay = (reports, dayId) => reports.find((r) => String(r.day_id) === String(dayId)) || null;

export default function Onboarding() {
  const location = useLocation();
  const [tab, setTab] = useState('onboarding');
  const [days, setDays] = useState([]);
  const [overview, setOverview] = useState(null);
  const [reports, setReports] = useState([]);
  const [activeDayId, setActiveDayId] = useState('');
  const [dayDetails, setDayDetails] = useState({});
  const [reportData, setReportData] = useState({ did: '', will_do: '', problems: '' });
  const [feedbackDrafts, setFeedbackDrafts] = useState({});
  const [quizDrafts, setQuizDrafts] = useState({});
  const [stepView, setStepView] = useState({});
  const [activeRegIndex, setActiveRegIndex] = useState(0);
  const [selectedRegulation, setSelectedRegulation] = useState(null);
  const [busyMap, setBusyMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const activeDay = useMemo(() => days.find((d) => String(d.id) === String(activeDayId)) || null, [days, activeDayId]);
  const activeDetail = activeDay ? dayDetails[String(activeDay.id)] : null;
  const activeReport = activeDay ? findReportByDay(reports, activeDay.id) : null;
  const tasks = activeDetail?.tasks || [];
  const regulations = activeDetail?.regulations || [];
  const reportStatus = normStatus(activeReport?.status);
  const firstTask = tasks[0] || null;
  const isDayOne = Number(activeDay?.day_number) === 1;
  const completedRegCount = regulations.filter((item) => item.is_read && item.has_feedback && item.has_passed_quiz).length;
  const activeRegulation = regulations[activeRegIndex] || null;

  const loadDayDetail = async (dayId, force = false) => {
    if (!dayId || (!force && dayDetails[String(dayId)])) return;
    const res = await onboardingAPI.getDay(dayId);
    const detail = res.data || {};
    setDayDetails((prev) => ({ ...prev, [String(dayId)]: detail }));
  };

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [daysRes, myRes, reportsRes] = await Promise.all([
        onboardingAPI.listDays(),
        onboardingAPI.getMy(),
        onboardingAPI.getReports(),
      ]);
      const nextDays = Array.isArray(daysRes.data) ? daysRes.data : [];
      const nextReports = Array.isArray(reportsRes.data) ? reportsRes.data : [];
      setDays(nextDays);
      setOverview(myRes.data || null);
      setReports(nextReports);

      if (nextDays.length > 0) {
        const dayNumberParam = Number(new URLSearchParams(location.search).get('day') || 0);
        const preferredByParam = dayNumberParam
          ? nextDays.find((d) => Number(d.day_number) === dayNumberParam)?.id
          : null;
        const current = preferredByParam || myRes.data?.current_day?.id || nextDays[0].id;
        setActiveDayId(String(current));
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось загрузить программу адаптации.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [location.search]);

  useEffect(() => {
    if (!activeDayId) return;
    setStepView({});
    setActiveRegIndex(0);
    loadDayDetail(activeDayId).catch(() => {});
  }, [activeDayId]);

  useEffect(() => {
    if (!regulations.length) {
      setActiveRegIndex(0);
      return;
    }
    const firstUnfinished = regulations.findIndex((item) => !(item.is_read && item.has_feedback && item.has_passed_quiz));
    const target = firstUnfinished === -1 ? regulations.length - 1 : firstUnfinished;
    setActiveRegIndex((prev) => {
      if (prev < 0 || prev >= regulations.length) return target;
      return prev > target ? target : prev;
    });
  }, [regulations]);

  useEffect(() => {
    if (!activeDay) return;
    const report = findReportByDay(reports, activeDay.id);
    setReportData({
      did: report?.did || '',
      will_do: report?.will_do || '',
      problems: report?.problems || '',
    });
  }, [activeDay, reports]);

  const markBusy = (key, value) => {
    setBusyMap((prev) => ({ ...prev, [key]: value }));
  };

  const completeCurrentDay = async () => {
    if (!activeDay) return;
    setSubmitting(true);
    setError('');
    try {
      await onboardingAPI.completeDay(activeDay.id);
      await load();
      await loadDayDetail(activeDay.id, true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось завершить день адаптации.');
    } finally {
      setSubmitting(false);
    }
  };

  const submitReport = async () => {
    if (!activeDay) return;
    if (!reportData.did.trim() || !reportData.will_do.trim()) {
      setError('Заполните поля "Что сделал" и "Что буду делать".');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const payload = { day_id: activeDay.id, ...reportData };
      if (activeReport?.id) {
        await onboardingAPI.updateReport(activeReport.id, reportData);
      } else {
        await onboardingAPI.submitReport(payload);
      }
      const reportsRes = await onboardingAPI.getReports();
      setReports(Array.isArray(reportsRes.data) ? reportsRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось отправить отчет.');
    } finally {
      setSubmitting(false);
    }
  };

  const markRegulationRead = async (regulationId) => {
    markBusy(`read-${regulationId}`, true);
    setError('');
    try {
      await regulationsAPI.markRead(regulationId);
      await loadDayDetail(activeDayId, true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось отметить регламент как прочитанный.');
    } finally {
      markBusy(`read-${regulationId}`, false);
    }
  };

  const submitRegulationFeedback = async (regulationId) => {
    const text = String(feedbackDrafts[regulationId] || '').trim();
    if (!text) {
      setError('Введите фидбек по регламенту.');
      return;
    }

    markBusy(`feedback-${regulationId}`, true);
    setError('');
    try {
      await regulationsAPI.sendFeedback(regulationId, { text });
      setFeedbackDrafts((prev) => ({ ...prev, [regulationId]: '' }));
      await loadDayDetail(activeDayId, true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось отправить фидбек по регламенту.');
    } finally {
      markBusy(`feedback-${regulationId}`, false);
    }
  };

  const submitRegulationQuiz = async (regulationId) => {
    const answer = String(quizDrafts[regulationId] || '').trim();
    if (!answer) {
      setError('Введите ответ на вопрос по регламенту.');
      return;
    }

    markBusy(`quiz-${regulationId}`, true);
    setError('');
    try {
      const res = await regulationsAPI.submitQuiz(regulationId, { answer });
      if (!res.data?.is_passed) {
        setError(res.data?.detail || 'Ответ не принят. Попробуйте еще раз.');
      } else {
        setQuizDrafts((prev) => ({ ...prev, [regulationId]: '' }));
      }
      await loadDayDetail(activeDayId, true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось отправить тест по регламенту.');
    } finally {
      markBusy(`quiz-${regulationId}`, false);
    }
  };

  const downloadRegulation = async (regulation) => {
    markBusy(`download-${regulation.id}`, true);
    setError('');
    try {
      const res = await api.get(`/v1/regulations/${regulation.id}/download/`, {
        responseType: 'blob',
      });
      const blob = res.data;
      const blobUrl = window.URL.createObjectURL(blob);
      const ext = (() => {
        const clean = String(regulation.content || '').split('?')[0].toLowerCase();
        if (clean.endsWith('.pdf')) return '.pdf';
        if (clean.endsWith('.docx')) return '.docx';
        if (clean.endsWith('.doc')) return '.doc';
        return '';
      })();
      const filename = `${regulation.title || 'regulation'}${ext}`.replace(/[\\/:*?"<>|]+/g, '_');
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      setError('Не удалось скачать файл. Проверьте авторизацию и попробуйте снова.');
    } finally {
      markBusy(`download-${regulation.id}`, false);
    }
  };

  return (
    <MainLayout title="Программа адаптации">
      <div className="page-header">
        <div>
          <div className="page-title">Программа адаптации</div>
          <div className="page-subtitle">Материалы, задачи и ежедневный отчет стажера</div>
        </div>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="card-body" style={{ color: '#b91c1c' }}>{error}</div>
        </div>
      )}

      {loading && (
        <div className="card">
          <div className="card-body">Загрузка...</div>
        </div>
      )}

      {!loading && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            {days.map((day) => {
              const done = overview?.days?.find((d) => String(d.day_id) === String(day.id))?.status === 'DONE';
              return (
                <button
                  key={day.id}
                  onClick={() => setActiveDayId(String(day.id))}
                  style={{
                    padding: '8px 18px',
                    borderRadius: 'var(--radius)',
                    border: '1px solid',
                    borderColor: String(activeDayId) === String(day.id) ? 'var(--primary)' : 'var(--gray-200)',
                    background: String(activeDayId) === String(day.id) ? 'var(--primary-light)' : 'white',
                    color: String(activeDayId) === String(day.id) ? 'var(--primary)' : 'var(--gray-700)',
                    fontWeight: 600,
                    fontSize: 13,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  День {day.day_number}
                  {done && <CheckCircle size={13} color="#16A34A" />}
                </button>
              );
            })}
          </div>

          <div className="tabs">
            <button className={`tab-btn ${tab === 'onboarding' ? 'active' : ''}`} onClick={() => setTab('onboarding')}>Онбординг</button>
            <button className={`tab-btn ${tab === 'tasks' ? 'active' : ''}`} onClick={() => setTab('tasks')}>Задачи</button>
            <button className={`tab-btn ${tab === 'report' ? 'active' : ''}`} onClick={() => setTab('report')}>Отчет</button>
          </div>

          {tab === 'onboarding' && activeDay && (
            <div className="onboarding-day-card">
              <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 6 }}>
                День {activeDay.day_number}. {activeDay.title}
              </h2>
              <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 16 }}>
                Дедлайн: {activeDay.deadline_time || 'Не задан'}
              </div>

              {isDayOne && (
                <div className="card" style={{ marginBottom: 16, border: '1px solid var(--gray-200)' }}>
                  <div className="card-body" style={{ padding: 16 }}>
                    <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>Задача Дня 1</div>
                    <div style={{ fontSize: 14, color: 'var(--gray-700)', marginBottom: 10 }}>
                      Прочитать все регламенты, затем по каждому отправить фидбек и пройти тест.
                    </div>
                    {firstTask?.due_date && (
                      <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 10 }}>
                        Дедлайн задачи: {firstTask.due_date}
                      </div>
                    )}
                    <button className="btn btn-primary" onClick={() => setTab('tasks')}>Открыть задачу</button>
                  </div>
                </div>
              )}

              <div style={{ color: 'var(--gray-600)', marginBottom: 20 }}>
                Регламенты и шаги выполнения находятся во вкладке <b>Задачи</b>.
              </div>

              <button className="btn btn-primary" disabled={submitting} onClick={completeCurrentDay}>
                Завершить день адаптации
              </button>
            </div>
          )}

          {tab === 'tasks' && (
            <div className="onboarding-day-card">
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>Задачи дня</div>
                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>{activeDay?.title || ''}</div>
              </div>

              {tasks.length === 0 && <div style={{ color: 'var(--gray-500)' }}>Задачи не назначены.</div>}
              {tasks.map((task) => (
                <div key={task.id} className="card" style={{ marginBottom: 10 }}>
                  <div className="card-body" style={{ padding: 14 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{task.title}</div>
                    {task.description && (
                      <div style={{ fontSize: 13, color: 'var(--gray-600)', marginTop: 4, whiteSpace: 'pre-line' }}>
                        {task.description}
                      </div>
                    )}
                    {task.due_date && <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 6 }}>Дедлайн: {task.due_date}</div>}
                  </div>
                </div>
              ))}

              {isDayOne && (
                <div className="card" style={{ marginTop: 14 }}>
                  <div className="card-body" style={{ padding: 14 }}>
                    <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>
                      Шаги по регламентам
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {regulations.length === 0 && <div style={{ color: 'var(--gray-500)' }}>На этот день регламенты не назначены.</div>}
                      {regulations.length > 0 && (
                        <div style={{ fontSize: 13, color: 'var(--gray-600)' }}>
                          Прогресс по регламентам: {completedRegCount}/{regulations.length}
                        </div>
                      )}
                      {activeRegulation && (() => {
                        const regulation = activeRegulation;
                        const index = activeRegIndex;
                        const regulationUrl = toAbsoluteMedia(regulation.content);
                        const isRead = !!regulation.is_read;
                        const hasFeedback = !!regulation.has_feedback;
                        const hasPassedQuiz = !!regulation.has_passed_quiz;
                        const currentStep = stepView[regulation.id] || 1;
                        const previousRegulationsDone = index === 0 || regulations
                          .slice(0, index)
                          .every((item) => item.is_read && item.has_feedback && item.has_passed_quiz);
                        const canDoStep1 = previousRegulationsDone;
                        const canDoStep2 = previousRegulationsDone && isRead;
                        const canDoStep3 = previousRegulationsDone && hasFeedback;
                        const goToStep = (step) => setStepView((prev) => ({ ...prev, [regulation.id]: step }));
                        return (
                          <div
                            key={regulation.id}
                            style={{
                              border: '1px solid var(--gray-200)',
                              borderRadius: 8,
                              padding: 12,
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start', marginBottom: 10 }}>
                              <div>
                                <div style={{ fontSize: 16, fontWeight: 700 }}>Шаг {index + 1}: {regulation.title}</div>
                              </div>
                              {regulationUrl ? (
                                <div style={{ display: 'flex', gap: 8 }}>
                                  <button
                                    className="btn btn-outline"
                                    onClick={() => setSelectedRegulation(regulation)}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                                  >
                                    <ExternalLink size={14} /> Подробнее
                                  </button>
                                  <button
                                    className="btn btn-secondary"
                                    onClick={() => downloadRegulation(regulation)}
                                    disabled={!!busyMap[`download-${regulation.id}`]}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                                  >
                                    <Download size={14} /> Скачать
                                  </button>
                                </div>
                              ) : null}
                            </div>

                            <div style={{ display: 'grid', gap: 12 }}>
                              {!previousRegulationsDone && (
                                <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                                  Этот регламент откроется после полного завершения предыдущего.
                                </div>
                              )}
                              {currentStep === 1 && (
                                <div className="card" style={{ border: '1px solid var(--gray-200)' }}>
                                  <div className="card-body" style={{ padding: 12 }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Шаг 1. Отметить, что прочитано</div>
                                    <div style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 10 }}>
                                      Откройте регламент через кнопку <b>Подробнее</b>, затем отметьте как прочитано.
                                    </div>
                                    <button
                                      className="btn btn-secondary"
                                      disabled={!canDoStep1 || isRead || !!busyMap[`read-${regulation.id}`]}
                                      onClick={() => markRegulationRead(regulation.id)}
                                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                                    >
                                      {isRead ? 'Прочитано' : 'Отметить как прочитано'}
                                    </button>
                                    {isRead && (
                                      <button className="btn btn-primary" style={{ marginLeft: 8 }} onClick={() => goToStep(2)}>
                                        Дальше
                                      </button>
                                    )}
                                  </div>
                                </div>
                              )}

                              {currentStep === 2 && (
                                <div className="card" style={{ border: '1px solid var(--gray-200)' }}>
                                  <div className="card-body" style={{ padding: 12 }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Шаг 2. Фидбек по регламенту</div>
                                    <textarea
                                      className="form-textarea"
                                      placeholder="Коротко напишите, что было не непонятно, если все понятно так и напишите"
                                      value={feedbackDrafts[regulation.id] || ''}
                                      onChange={(e) => setFeedbackDrafts((prev) => ({ ...prev, [regulation.id]: e.target.value }))}
                                      disabled={!canDoStep2 || hasFeedback}
                                      style={{ minHeight: 82, marginBottom: 8 }}
                                    />
                                    <button
                                      className="btn btn-secondary"
                                      disabled={!canDoStep2 || hasFeedback || !!busyMap[`feedback-${regulation.id}`]}
                                      onClick={() => submitRegulationFeedback(regulation.id)}
                                    >
                                      {hasFeedback ? 'Фидбек отправлен' : 'Отправить фидбек'}
                                    </button>
                                    {hasFeedback && (
                                      <button className="btn btn-primary" style={{ marginLeft: 8 }} onClick={() => goToStep(3)}>
                                        Дальше
                                      </button>
                                    )}
                                  </div>
                                </div>
                              )}

                              {currentStep === 3 && (
                                <div className="card" style={{ border: '1px solid var(--gray-200)' }}>
                                  <div className="card-body" style={{ padding: 12 }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Шаг 3. Тест на знание</div>
                                    <div style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 6 }}>
                                      {regulation.quiz_question || 'Подтвердите знание регламента в свободной форме.'}
                                    </div>
                                    <input
                                      className="form-input"
                                      placeholder="Введите ответ"
                                      value={quizDrafts[regulation.id] || ''}
                                      onChange={(e) => setQuizDrafts((prev) => ({ ...prev, [regulation.id]: e.target.value }))}
                                      disabled={!canDoStep3 || hasPassedQuiz}
                                      style={{ marginBottom: 8 }}
                                    />
                                    <button
                                      className="btn btn-secondary"
                                      disabled={!canDoStep3 || hasPassedQuiz || !!busyMap[`quiz-${regulation.id}`]}
                                      onClick={() => submitRegulationQuiz(regulation.id)}
                                    >
                                      {hasPassedQuiz ? 'Тест пройден' : 'Отправить ответ'}
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>

                            <div style={{ marginTop: 12, display: 'flex', gap: 10, fontSize: 13 }}>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                {isRead ? <CheckCircle size={14} color="#16A34A" /> : <Circle size={14} color="#9CA3AF" />} Прочитан
                              </span>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                {hasFeedback ? <CheckCircle size={14} color="#16A34A" /> : <Circle size={14} color="#9CA3AF" />} Фидбек
                              </span>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                {hasPassedQuiz ? <CheckCircle size={14} color="#16A34A" /> : <Circle size={14} color="#9CA3AF" />} Тест
                              </span>
                            </div>

                            {isRead && hasFeedback && hasPassedQuiz && index < regulations.length - 1 && (
                              <div style={{ marginTop: 12 }}>
                                <button
                                  className="btn btn-primary"
                                  onClick={() => {
                                    setActiveRegIndex(index + 1);
                                    const next = regulations[index + 1];
                                    if (next) {
                                      setStepView((prev) => ({ ...prev, [next.id]: prev[next.id] || 1 }));
                                    }
                                  }}
                                >
                                  Следующий регламент
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'report' && (
            <div className="onboarding-day-card">
              <div style={{ marginBottom: 14, fontSize: 13, color: 'var(--gray-500)' }}>
                Статус: {STATUS_LABELS[reportStatus]}
              </div>

              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Что сделал</label>
                <textarea
                  className="form-textarea"
                  value={reportData.did}
                  onChange={(e) => setReportData((prev) => ({ ...prev, did: e.target.value }))}
                  style={{ minHeight: 120 }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Что буду делать</label>
                <textarea
                  className="form-textarea"
                  value={reportData.will_do}
                  onChange={(e) => setReportData((prev) => ({ ...prev, will_do: e.target.value }))}
                  style={{ minHeight: 120 }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Проблемы</label>
                <textarea
                  className="form-textarea"
                  value={reportData.problems}
                  onChange={(e) => setReportData((prev) => ({ ...prev, problems: e.target.value }))}
                  style={{ minHeight: 100 }}
                />
              </div>

              <button className="btn btn-primary" disabled={submitting} onClick={submitReport} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <Send size={14} /> {submitting ? 'Отправка...' : 'Сохранить отчет'}
              </button>
            </div>
          )}

          {selectedRegulation && (
            <div className="modal-overlay" onClick={() => setSelectedRegulation(null)}>
              <div className="modal" style={{ maxWidth: 980, width: 'calc(100vw - 32px)' }} onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <div className="modal-title">{selectedRegulation.title}</div>
                  <button className="btn-icon" type="button" onClick={() => setSelectedRegulation(null)}><X size={18} /></button>
                </div>
                <div className="modal-body">
                  <div
                    style={{
                      maxHeight: '65vh',
                      overflowY: 'auto',
                      border: '1px solid var(--gray-200)',
                      borderRadius: 8,
                      background: '#fff',
                      padding: 12,
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.55,
                      fontSize: 13,
                      color: 'var(--gray-800)',
                    }}
                  >
                    {String(selectedRegulation.description || '').trim() || 'Текст регламента пока недоступен.'}
                  </div>
                </div>
                <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => downloadRegulation(selectedRegulation)}
                    disabled={!!busyMap[`download-${selectedRegulation.id}`]}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  >
                    <Download size={14} /> Скачать
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}
