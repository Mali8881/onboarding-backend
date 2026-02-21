import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API = {
  accounts: 'http://127.0.0.1:8000/api/v1/accounts',
  content: 'http://127.0.0.1:8000/api/v1/content',
  regulations: 'http://127.0.0.1:8000/api/v1/regulations',
  reports: 'http://127.0.0.1:8000/api/v1/reports',
  schedule: 'http://127.0.0.1:8000/api',
  common: 'http://127.0.0.1:8000/api/v1/common',
}

const STORAGE_TOKEN = 'onboarding_access_token'
const STORAGE_LANDING = 'onboarding_landing'
const STORAGE_ROLE = 'onboarding_role'

function getErrorMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  return data.detail || data.error || fallback
}

function landingFromRole(role) {
  if (role === 'ADMIN' || role === 'SUPER_ADMIN') return 'admin_panel'
  if (role === 'INTERN') return 'intern_portal'
  return 'employee_portal'
}

async function toJson(res) {
  try {
    return await res.json()
  } catch {
    return null
  }
}

function App() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(localStorage.getItem(STORAGE_TOKEN) || '')
  const [role, setRole] = useState(localStorage.getItem(STORAGE_ROLE) || '')
  const [landing, setLanding] = useState(localStorage.getItem(STORAGE_LANDING) || '')
  const [isFirstLogin, setIsFirstLogin] = useState(false)
  const [fullName, setFullName] = useState('')
  const [globalError, setGlobalError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  const [internOverview, setInternOverview] = useState(null)
  const [internLoading, setInternLoading] = useState(false)
  const [internError, setInternError] = useState('')
  const [feedbackTextByRegulation, setFeedbackTextByRegulation] = useState({})
  const [internSubmitting, setInternSubmitting] = useState(false)

  const [employeeHome, setEmployeeHome] = useState(null)
  const [employeeCoursesMy, setEmployeeCoursesMy] = useState([])
  const [employeeCoursesCatalog, setEmployeeCoursesCatalog] = useState([])
  const [employeeReports, setEmployeeReports] = useState([])
  const [employeeSchedule, setEmployeeSchedule] = useState(null)
  const [employeeScheduleOptions, setEmployeeScheduleOptions] = useState([])
  const [employeeScheduleChoice, setEmployeeScheduleChoice] = useState('')
  const [companyStructure, setCompanyStructure] = useState(null)
  const [employeeError, setEmployeeError] = useState('')
  const [employeeTab, setEmployeeTab] = useState('home')
  const [employeeLoading, setEmployeeLoading] = useState(false)
  const [dailyReportSummary, setDailyReportSummary] = useState('')

  const [adminRequests, setAdminRequests] = useState([])
  const [adminDepartments, setAdminDepartments] = useState([])
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminError, setAdminError] = useState('')
  const [employeeActionLoading, setEmployeeActionLoading] = useState(false)

  const authHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }),
    [token],
  )

  const enrolledCourseIds = useMemo(
    () => new Set((employeeCoursesMy || []).map((item) => item.course?.id)),
    [employeeCoursesMy],
  )

  useEffect(() => {
    if (!token) {
      setRole('')
      setLanding('')
      setFullName('')
      return
    }
    hydrateSession()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!token || !landing) return
    if (landing === 'intern_portal') loadInternOverview()
    if (landing === 'employee_portal') loadEmployeeData()
    if (landing === 'admin_panel') loadAdminData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [landing, token])

  async function hydrateSession() {
    setGlobalError('')
    const res = await fetch(`${API.accounts}/me/profile/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await toJson(res)
    if (!res.ok) {
      resetSession()
      setGlobalError(getErrorMessage(data, 'Сессия истекла. Войдите заново.'))
      return
    }

    const nextRole = data?.role || ''
    setRole(nextRole)
    localStorage.setItem(STORAGE_ROLE, nextRole)
    const nextLanding = landing || landingFromRole(nextRole)
    setLanding(nextLanding)
    localStorage.setItem(STORAGE_LANDING, nextLanding)

    const name = `${data.first_name || ''} ${data.last_name || ''}`.trim() || data.username || ''
    setFullName(name)
  }

  async function handleLogin(event) {
    event.preventDefault()
    setGlobalError('')
    setAuthLoading(true)

    try {
      const res = await fetch(`${API.accounts}/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await toJson(res)
      if (!res.ok) throw new Error(getErrorMessage(data, 'Неверный логин или пароль'))

      const nextToken = data.access
      const nextLanding = data.landing || landingFromRole(data?.user?.role)
      const nextRole = data?.user?.role || ''
      setIsFirstLogin(Boolean(data?.user?.is_first_login))

      localStorage.setItem(STORAGE_TOKEN, nextToken)
      localStorage.setItem(STORAGE_LANDING, nextLanding)
      localStorage.setItem(STORAGE_ROLE, nextRole)

      setToken(nextToken)
      setLanding(nextLanding)
      setRole(nextRole)
      setPassword('')
      setUsername('')
    } catch (error) {
      setGlobalError(error.message || 'Ошибка входа')
    } finally {
      setAuthLoading(false)
    }
  }

  function resetSession() {
    localStorage.removeItem(STORAGE_TOKEN)
    localStorage.removeItem(STORAGE_LANDING)
    localStorage.removeItem(STORAGE_ROLE)
    setToken('')
    setRole('')
    setLanding('')
    setFullName('')
    setIsFirstLogin(false)
  }

  async function loadInternOverview() {
    setInternLoading(true)
    setInternError('')
    try {
      const res = await fetch(`${API.regulations}/intern/overview/`, { headers: authHeaders })
      const data = await toJson(res)
      if (!res.ok) throw new Error(getErrorMessage(data, 'Не удалось загрузить страницу стажера'))
      setInternOverview(data)
    } catch (error) {
      setInternError(error.message || 'Ошибка страницы стажера')
    } finally {
      setInternLoading(false)
    }
  }

  async function startInternOnboarding() {
    const res = await fetch(`${API.regulations}/intern/start/`, {
      method: 'POST',
      headers: authHeaders,
    })
    const data = await toJson(res)
    if (!res.ok) {
      setInternError(getErrorMessage(data, 'Не удалось начать обучение'))
      return
    }
    setIsFirstLogin(false)
    loadInternOverview()
  }

  async function markRegulationRead(regulationId) {
    const res = await fetch(`${API.regulations}/${regulationId}/read/`, {
      method: 'POST',
      headers: authHeaders,
    })
    const data = await toJson(res)
    if (!res.ok) {
      setInternError(getErrorMessage(data, 'Не удалось отметить регламент как прочитанный'))
      return
    }
    loadInternOverview()
  }

  async function submitRegulationFeedback(regulationId) {
    const text = (feedbackTextByRegulation[regulationId] || '').trim()
    if (!text) return
    const res = await fetch(`${API.regulations}/${regulationId}/feedback/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ text }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setInternError(getErrorMessage(data, 'Не удалось отправить обратную связь'))
      return
    }
    setFeedbackTextByRegulation((prev) => ({ ...prev, [regulationId]: '' }))
  }

  async function submitInternCompletion() {
    setInternSubmitting(true)
    setInternError('')
    const res = await fetch(`${API.regulations}/intern/submit/`, {
      method: 'POST',
      headers: authHeaders,
    })
    const data = await toJson(res)
    if (!res.ok) {
      setInternError(getErrorMessage(data, 'Не удалось отправить завершение обучения'))
      setInternSubmitting(false)
      return
    }
    await loadInternOverview()
    setInternSubmitting(false)
  }

  async function loadEmployeeData() {
    setEmployeeLoading(true)
    setEmployeeError('')
    try {
      const [homeRes, myRes, catalogRes, reportsRes, scheduleRes, scheduleOptionsRes, structureRes] = await Promise.all([
        fetch(`${API.accounts}/employee/home/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/my/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/available/`, { headers: authHeaders }),
        fetch(`${API.reports}/employee/daily/`, { headers: authHeaders }),
        fetch(`${API.schedule}/my-schedule/`, { headers: authHeaders }),
        fetch(`${API.schedule}/schedules/`, { headers: authHeaders }),
        fetch(`${API.accounts}/company/structure/`, { headers: authHeaders }),
      ])

      const [
        homeData,
        myData,
        catalogData,
        reportsData,
        scheduleData,
        scheduleOptionsData,
        structureData,
      ] = await Promise.all([
        toJson(homeRes),
        toJson(myRes),
        toJson(catalogRes),
        toJson(reportsRes),
        toJson(scheduleRes),
        toJson(scheduleOptionsRes),
        toJson(structureRes),
      ])

      if (!homeRes.ok) throw new Error(getErrorMessage(homeData, 'Не удалось загрузить страницу работника'))
      setEmployeeHome(homeData)
      setEmployeeCoursesMy(Array.isArray(myData) ? myData : [])
      setEmployeeCoursesCatalog(Array.isArray(catalogData) ? catalogData : [])
      setEmployeeReports(Array.isArray(reportsData) ? reportsData : [])
      setEmployeeSchedule(scheduleRes.ok ? scheduleData : null)
      setEmployeeScheduleOptions(scheduleOptionsRes.ok && Array.isArray(scheduleOptionsData) ? scheduleOptionsData : [])
      setCompanyStructure(structureRes.ok ? structureData : null)
    } catch (error) {
      setEmployeeError(error.message || 'Ошибка страницы работника')
    } finally {
      setEmployeeLoading(false)
    }
  }

  async function submitDailyReport(event) {
    event.preventDefault()
    const summary = dailyReportSummary.trim()
    if (!summary) return
    const res = await fetch(`${API.reports}/employee/daily/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ summary }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось отправить отчет'))
      return
    }
    setDailyReportSummary('')
    loadEmployeeData()
  }

  async function enrollEmployeeCourse(courseId) {
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.content}/courses/self-enroll/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ course_id: courseId }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось принять курс'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    loadEmployeeData()
  }

  async function chooseEmployeeSchedule(event) {
    event.preventDefault()
    if (!employeeScheduleChoice) return
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.schedule}/choose-schedule/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ schedule_id: Number(employeeScheduleChoice) }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось отправить график'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    loadEmployeeData()
  }

  async function loadAdminData() {
    setAdminLoading(true)
    setAdminError('')
    try {
      const [requestsRes, profileRes, notificationsRes] = await Promise.all([
        fetch(`${API.regulations}/admin/intern-requests/?status=pending`, { headers: authHeaders }),
        fetch(`${API.accounts}/me/profile/`, { headers: authHeaders }),
        fetch(`${API.common}/notifications/`, { headers: authHeaders }),
      ])
      const [requestsData, profileData, notificationsData] = await Promise.all([
        toJson(requestsRes),
        toJson(profileRes),
        toJson(notificationsRes),
      ])
      if (!requestsRes.ok) throw new Error(getErrorMessage(requestsData, 'Не удалось загрузить заявки стажеров'))
      setAdminRequests(Array.isArray(requestsData) ? requestsData : [])

      const departments = profileData?.department ? [{ id: profileData.department_id, name: profileData.department }] : []
      setAdminDepartments(departments)

      if (!notificationsRes.ok) {
        setAdminError('Заявки загружены, но уведомления недоступны.')
      } else if (notificationsData?.unread_count > 0) {
        setAdminError(`Непрочитанные уведомления: ${notificationsData.unread_count}`)
      }
    } catch (error) {
      setAdminError(error.message || 'Ошибка страницы администратора')
    } finally {
      setAdminLoading(false)
    }
  }

  async function approveInternRequest(requestId, departmentId) {
    const payload = departmentId ? { department_id: Number(departmentId) } : {}
    const res = await fetch(`${API.regulations}/admin/intern-requests/${requestId}/approve/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify(payload),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setAdminError(getErrorMessage(data, 'Не удалось подтвердить заявку'))
      return
    }
    loadAdminData()
  }

  function renderLogin() {
    return (
      <section className="panel auth-panel">
        <h1>Единый вход в систему</h1>
        <p>Один логин для стажера, работника, админа и суперадмина.</p>
        <form onSubmit={handleLogin}>
          <label>
            Логин
            <input value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={authLoading}>
            {authLoading ? 'Входим...' : 'Войти'}
          </button>
        </form>
      </section>
    )
  }

  function renderInternPortal() {
    const items = internOverview?.items || []
    return (
      <section className="panel">
        <h2>Кабинет стажера</h2>
        <p>{internOverview?.welcome || `Здравствуйте, ${fullName}`}</p>

        {(isFirstLogin || internOverview?.is_first_login) && (
          <div className="inline-block">
            <p>Это ваш первый вход. Нажмите, чтобы начать обучение.</p>
            <button onClick={startInternOnboarding}>Начать обучение</button>
          </div>
        )}

        <div className="stats">
          <span>Всего регламентов: {internOverview?.total_regulations || 0}</span>
          <span>Прочитано: {internOverview?.read_regulations || 0}</span>
        </div>

        <div className="progress-wrap">
          <div className="progress-label">
            <span>Прогресс чтения</span>
            <span>{internOverview?.progress_percent ?? 0}%</span>
          </div>
          <div className="progress-line">
            <div style={{ width: `${internOverview?.progress_percent ?? 0}%` }} />
          </div>
        </div>

        {internOverview?.next_step_message && <p className="notice">{internOverview.next_step_message}</p>}
        {internOverview?.request_status && <p>Статус заявки: {internOverview.request_status}</p>}
        {internError && <p className="error">{internError}</p>}
        {internLoading && <p>Загрузка...</p>}

        {!internLoading &&
          items.map((item) => (
            <article className="card" key={item.regulation.id}>
              <h3>{item.regulation.title}</h3>
              <p>{item.regulation.description || 'Описание отсутствует'}</p>
              <div className="actions-row">
                <button disabled={item.is_read} onClick={() => markRegulationRead(item.regulation.id)}>
                  {item.is_read ? 'Прочитано' : 'Отметить как прочитано'}
                </button>
              </div>
              <div className="feedback-row">
                <textarea
                  placeholder="Предложить правки к регламенту"
                  value={feedbackTextByRegulation[item.regulation.id] || ''}
                  onChange={(event) =>
                    setFeedbackTextByRegulation((prev) => ({
                      ...prev,
                      [item.regulation.id]: event.target.value,
                    }))
                  }
                />
                <button onClick={() => submitRegulationFeedback(item.regulation.id)}>Отправить обратную связь</button>
              </div>
            </article>
          ))}

        <div className="footer-action">
          <button disabled={!internOverview?.all_read || internSubmitting} onClick={submitInternCompletion}>
            {internSubmitting ? 'Отправка...' : 'Завершить обучение'}
          </button>
        </div>
      </section>
    )
  }

  function renderEmployeePortal() {
    return (
      <section className="panel">
        <h2>Кабинет работника</h2>
        <p>{employeeHome?.greeting || `Здравствуйте, ${fullName}`}</p>
        {employeeError && <p className="error">{employeeError}</p>}
        {employeeLoading && <p>Загрузка...</p>}

        <nav className="tabs">
          <button className={employeeTab === 'home' ? 'active' : ''} onClick={() => setEmployeeTab('home')}>
            Главная
          </button>
          <button className={employeeTab === 'my_courses' ? 'active' : ''} onClick={() => setEmployeeTab('my_courses')}>
            Мои курсы
          </button>
          <button className={employeeTab === 'catalog' ? 'active' : ''} onClick={() => setEmployeeTab('catalog')}>
            Каталог курсов
          </button>
          <button className={employeeTab === 'reports' ? 'active' : ''} onClick={() => setEmployeeTab('reports')}>
            Отчеты
          </button>
          <button className={employeeTab === 'schedule' ? 'active' : ''} onClick={() => setEmployeeTab('schedule')}>
            График работы
          </button>
          <button className={employeeTab === 'structure' ? 'active' : ''} onClick={() => setEmployeeTab('structure')}>
            Структура компании
          </button>
        </nav>

        {employeeTab === 'home' && (
          <div className="card">
            <p>Мои курсы: {employeeHome?.my_courses_count || 0}</p>
            <p>Завершенные курсы: {employeeHome?.completed_courses_count || 0}</p>
            <p>Доступные курсы: {employeeHome?.available_courses_count || 0}</p>
            <p>Ежедневные отчеты: {employeeHome?.daily_reports_count || 0}</p>
          </div>
        )}

        {employeeTab === 'my_courses' &&
          employeeCoursesMy.map((item) => (
            <article className="card" key={item.id}>
              <h3>{item.course.title}</h3>
              <p>Статус: {item.status}</p>
              <p>Прогресс: {item.progress_percent}%</p>
            </article>
          ))}

        {employeeTab === 'catalog' &&
          employeeCoursesCatalog.map((course) => (
            <article className="card" key={course.id}>
              <h3>{course.title}</h3>
              <p>{course.description || 'Описание отсутствует'}</p>
              <p>Тип: {course.visibility}</p>
              <button
                disabled={employeeActionLoading || enrolledCourseIds.has(course.id)}
                onClick={() => enrollEmployeeCourse(course.id)}
              >
                {enrolledCourseIds.has(course.id) ? 'Уже в моих курсах' : 'Принять курс'}
              </button>
            </article>
          ))}

        {employeeTab === 'reports' && (
          <div>
            <form className="inline-form" onSubmit={submitDailyReport}>
              <textarea
                value={dailyReportSummary}
                onChange={(event) => setDailyReportSummary(event.target.value)}
                placeholder="Краткий итог рабочего дня"
              />
              <button type="submit">Отправить ежедневный отчет</button>
            </form>
            {employeeReports.map((report) => (
              <article className="card" key={report.id}>
                <p>Дата: {report.report_date}</p>
                <p>{report.summary}</p>
              </article>
            ))}
          </div>
        )}

        {employeeTab === 'schedule' && (
          <article className="card">
            <form className="inline-form" onSubmit={chooseEmployeeSchedule}>
              <label>
                Выберите график на неделю
                <select value={employeeScheduleChoice} onChange={(event) => setEmployeeScheduleChoice(event.target.value)}>
                  <option value="">-- выберите график --</option>
                  {employeeScheduleOptions.map((item) => (
                    <option value={item.id} key={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" disabled={employeeActionLoading || !employeeScheduleChoice}>
                {employeeActionLoading ? 'Отправка...' : 'Сохранить график'}
              </button>
            </form>
            {employeeSchedule ? (
              <>
                <p>Статус: {employeeSchedule.status || 'неизвестно'}</p>
                <p>График: {employeeSchedule.name || employeeSchedule.schedule || 'не выбран'}</p>
              </>
            ) : (
              <p>График пока не выбран.</p>
            )}
          </article>
        )}

        {employeeTab === 'structure' && (
          <div>
            <article className="card">
              <h3>Владелец</h3>
              <p>{companyStructure?.owner?.full_name || 'Николай'}</p>
            </article>
            {(companyStructure?.departments || []).map((department) => (
              <article className="card" key={department.id}>
                <h3>{department.name}</h3>
                <p>Руководитель: {department.head?.full_name || department.head?.username || 'Не назначен'}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    )
  }

  function renderAdminPortal() {
    return (
      <section className="panel">
        <h2>Панель администратора</h2>
        <p>Здравствуйте, {fullName}</p>
        {adminError && <p className="error">{adminError}</p>}
        {adminLoading && <p>Загрузка...</p>}

        <h3>Заявки стажеров на завершение</h3>
        {adminRequests.length === 0 && <p>Нет заявок в ожидании.</p>}
        {adminRequests.map((request) => (
          <article className="card" key={request.id}>
            <p>Стажер: {request.username}</p>
            <p>Статус: {request.status}</p>
            <div className="actions-row">
              <select id={`dep-${request.id}`} defaultValue="">
                <option value="">Без отдела</option>
                {adminDepartments.map((department) => (
                  <option value={department.id} key={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => {
                  const select = document.getElementById(`dep-${request.id}`)
                  approveInternRequest(request.id, select?.value || '')
                }}
              >
                Подтвердить и перевести в работника
              </button>
            </div>
          </article>
        ))}
      </section>
    )
  }

  return (
    <main className="layout">
      <header className="topbar">
        <div>
          <strong>Система онбординга</strong>
          <p>Единый вход для всех ролей</p>
        </div>
        {token && (
          <div className="session-actions">
            <span>{role || 'Неизвестная роль'}</span>
            <button onClick={resetSession}>Выйти</button>
          </div>
        )}
      </header>

      {!token && renderLogin()}
      {globalError && <p className="error">{globalError}</p>}
      {token && landing === 'intern_portal' && renderInternPortal()}
      {token && landing === 'employee_portal' && renderEmployeePortal()}
      {token && landing === 'admin_panel' && renderAdminPortal()}
    </main>
  )
}

export default App
