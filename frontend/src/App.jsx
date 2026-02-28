import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API = {
  accounts: 'http://127.0.0.1:8000/api/v1/accounts',
  content: 'http://127.0.0.1:8000/api/v1/content',
  regulations: 'http://127.0.0.1:8000/api/v1/regulations',
  reports: 'http://127.0.0.1:8000/api/v1/reports',
  tasks: 'http://127.0.0.1:8000/api/v1/tasks',
  kb: 'http://127.0.0.1:8000/api/v1/kb',
  metrics: 'http://127.0.0.1:8000/api/v1/metrics',
  bpm: 'http://127.0.0.1:8000/api/v1/bpm',
  schedule: 'http://127.0.0.1:8000/api',
  common: 'http://127.0.0.1:8000/api/v1/common',
}

const STORAGE_TOKEN = 'onboarding_access_token'
const STORAGE_LANDING = 'onboarding_landing'
const STORAGE_ROLE = 'onboarding_role'
const WEEKDAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function getErrorMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (Array.isArray(data)) return data[0] || fallback
  if (typeof data === 'object') {
    const firstKey = Object.keys(data)[0]
    if (firstKey) {
      const firstValue = data[firstKey]
      if (Array.isArray(firstValue)) return `${firstKey}: ${firstValue[0]}`
      if (typeof firstValue === 'string') return `${firstKey}: ${firstValue}`
    }
  }
  return data.detail || data.error || fallback
}

function parseISODate(isoDate) {
  if (!isoDate || typeof isoDate !== 'string') return null
  const [yearStr, monthStr, dayStr] = isoDate.split('-')
  const year = Number(yearStr)
  const month = Number(monthStr)
  const day = Number(dayStr)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function formatLocalISO(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function landingFromRole(role) {
  if (role === 'ADMIN' || role === 'SUPER_ADMIN') return 'admin_panel'
  if (role === 'INTERN') return 'intern_portal'
  if (role === 'TEAMLEAD') return 'teamlead_portal'
  return 'employee_portal'
}

async function toJson(res) {
  try {
    return await res.json()
  } catch {
    return null
  }
}

function getMondayISO(baseDate = new Date()) {
  const current = new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate())
  const day = current.getDay()
  const diffToMonday = (day + 6) % 7
  current.setDate(current.getDate() - diffToMonday)
  return formatLocalISO(current)
}

function addDaysISO(isoDate, daysToAdd) {
  const value = parseISODate(isoDate)
  if (!value) return isoDate
  value.setDate(value.getDate() + daysToAdd)
  return formatLocalISO(value)
}

function normalizeWeekStartISO(isoDate) {
  const parsed = parseISODate(isoDate)
  if (!parsed) return getCurrentPlanningMondayISO()
  const day = parsed.getDay()
  const diffToMonday = (day + 6) % 7
  parsed.setDate(parsed.getDate() - diffToMonday)
  return formatLocalISO(parsed)
}

function getCurrentPlanningMondayISO(baseDate = new Date()) {
  const currentMonday = getMondayISO(baseDate)
  const day = baseDate.getDay()
  if (day === 6 || day === 0) return addDaysISO(currentMonday, 7)
  return currentMonday
}

function getDayHourLimits(isoDate) {
  const parsed = parseISODate(isoDate)
  if (!parsed) return { min: '09:00', max: '21:00' }
  const weekday = parsed.getDay()
  if (weekday >= 1 && weekday <= 5) {
    return { min: '09:00', max: '21:00' }
  }
  return { min: '11:00', max: '19:00' }
}

function makeEmptyShift(date = '', dayIndex = 0) {
  const limits = getDayHourLimits(date)
  const defaultEndHour = dayIndex < 5 ? '17:00' : '19:00'
  return {
    date,
    start_time: limits.min,
    end_time: defaultEndHour,
    mode: 'office',
    comment: '',
    breaks: [],
    lunch_start: '',
    lunch_end: '',
  }
}

function createFixedWeekShifts(weekStart, sourceDays = []) {
  const byDate = new Map(
    (Array.isArray(sourceDays) ? sourceDays : [])
      .filter((item) => item && item.date)
      .map((item) => [item.date, item]),
  )
  return weekDates(weekStart).map((weekDay, index) => {
    const source = byDate.get(weekDay.date)
    if (!source) return makeEmptyShift(weekDay.date, index)
    const limits = getDayHourLimits(weekDay.date)
    return {
      date: weekDay.date,
      start_time: source.mode === 'day_off' ? '' : (source.start_time || limits.min),
      end_time: source.mode === 'day_off' ? '' : (source.end_time || (index < 5 ? '17:00' : '19:00')),
      mode: source.mode === 'online' || source.mode === 'day_off' ? source.mode : 'office',
      comment: source.comment || '',
      breaks: Array.isArray(source.breaks)
        ? source.breaks
            .filter((item) => item && item.start_time && item.end_time)
            .map((item) => ({
              start_time: item.start_time,
              end_time: (() => {
                const startMinutes = hhmmToMinutes(item.start_time)
                return startMinutes === null ? item.end_time : minutesToHHMM(startMinutes + 15)
              })(),
            }))
        : [],
      lunch_start: source.lunch_start || '',
      lunch_end: source.lunch_start
        ? (() => {
            const startMinutes = hhmmToMinutes(source.lunch_start)
            return startMinutes === null ? (source.lunch_end || '') : minutesToHHMM(startMinutes + 60)
          })()
        : '',
    }
  })
}

function getShiftHours(shift) {
  if (shift?.mode === 'day_off') return 0
  if (!shift?.start_time || !shift?.end_time) return 0
  const [startHour] = shift.start_time.split(':').map(Number)
  const [endHour] = shift.end_time.split(':').map(Number)
  if (Number.isNaN(startHour) || Number.isNaN(endHour)) return 0
  const diff = endHour - startHour
  if (diff <= 0) return 0
  return diff
}

function hhmmToMinutes(value) {
  if (!value || typeof value !== 'string') return null
  const [h, m] = value.split(':').map(Number)
  if (Number.isNaN(h) || Number.isNaN(m)) return null
  return h * 60 + m
}

function minutesToHHMM(totalMinutes) {
  const normalized = ((totalMinutes % (24 * 60)) + (24 * 60)) % (24 * 60)
  const h = String(Math.floor(normalized / 60)).padStart(2, '0')
  const m = String(normalized % 60).padStart(2, '0')
  return `${h}:${m}`
}

function canUseShortBreaks(shift) {
  return shift?.mode === 'office' && getShiftHours(shift) >= 7
}

function canUseLunchBreak(shift) {
  return shift?.mode === 'office' && getShiftHours(shift) >= 8
}

function normalizeShiftBreakRules(shift) {
  if (!shift || shift.mode !== 'office') {
    return { ...(shift || {}), breaks: [], lunch_start: '', lunch_end: '' }
  }
  const next = { ...shift }
  if (!canUseShortBreaks(next)) {
    next.breaks = []
  } else {
    next.breaks = Array.isArray(next.breaks) ? next.breaks.slice(0, 4) : []
  }
  if (!canUseLunchBreak(next)) {
    next.lunch_start = ''
    next.lunch_end = ''
  } else {
    next.lunch_start = next.lunch_start || ''
    if (next.lunch_start) {
      const startMinutes = hhmmToMinutes(next.lunch_start)
      next.lunch_end = startMinutes === null ? '' : minutesToHHMM(startMinutes + 60)
    } else {
      next.lunch_end = ''
    }
  }
  return next
}

function sumShiftHours(shifts, mode) {
  return (shifts || []).reduce((acc, shift) => {
    if (shift.mode !== mode) return acc
    return acc + getShiftHours(shift)
  }, 0)
}

function formatShiftWeekday(isoDate) {
  if (!isoDate) return ''
  const parsed = parseISODate(isoDate)
  if (!parsed) return ''
  const weekday = (parsed.getDay() + 6) % 7
  return WEEKDAY_LABELS[weekday] || ''
}

function isShiftInsideWeek(isoDate, weekStart) {
  if (!isoDate || !weekStart) return false
  const shiftDate = parseISODate(isoDate)
  const monday = parseISODate(weekStart)
  if (!shiftDate || !monday) return false
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return shiftDate >= monday && shiftDate <= sunday
}

function weekDates(weekStart) {
  const mondayISO = normalizeWeekStartISO(weekStart)
  if (!mondayISO) return []
  return Array.from({ length: 7 }, (_, i) => {
    return {
      dayLabel: WEEKDAY_LABELS[i],
      date: addDaysISO(mondayISO, i),
    }
  })
}

function pickPlannableWeekStart(plans, baseDate = new Date()) {
  const approvedWeeks = new Set((plans || []).filter((x) => x.status === 'approved').map((x) => x.week_start))
  let candidate = getCurrentPlanningMondayISO(baseDate)
  while (approvedWeeks.has(candidate)) {
    candidate = addDaysISO(candidate, 7)
  }
  return candidate
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
  const [employeeWeeklyPlans, setEmployeeWeeklyPlans] = useState([])
  const [employeeWeekStart, setEmployeeWeekStart] = useState(getCurrentPlanningMondayISO())
  const [employeeWeekDays, setEmployeeWeekDays] = useState(() => createFixedWeekShifts(getCurrentPlanningMondayISO()))
  const [employeeOnlineReason, setEmployeeOnlineReason] = useState('')
  const [employeeWeekComment, setEmployeeWeekComment] = useState('')
  const [companyStructure, setCompanyStructure] = useState(null)
  const [employeeError, setEmployeeError] = useState('')
  const [employeeTab, setEmployeeTab] = useState('home')
  const [employeeLoading, setEmployeeLoading] = useState(false)
  const [dailyReportSummary, setDailyReportSummary] = useState('')
  const [employeeTasksMy, setEmployeeTasksMy] = useState([])
  const [employeeTasksTeam, setEmployeeTasksTeam] = useState([])
  const [employeeTaskCreate, setEmployeeTaskCreate] = useState({ title: '', description: '', assignee_id: '' })
  const [kbArticles, setKbArticles] = useState([])
  const [kbReport, setKbReport] = useState(null)
  const [myMetrics, setMyMetrics] = useState(null)
  const [teamMetrics, setTeamMetrics] = useState(null)
  const [bpmItems, setBpmItems] = useState([])
  const [bpmTemplates, setBpmTemplates] = useState([])
  const [selectedTaskId, setSelectedTaskId] = useState('')
  const [selectedTaskColumn, setSelectedTaskColumn] = useState('')

  const [adminRequests, setAdminRequests] = useState([])
  const [adminDepartments, setAdminDepartments] = useState([])
  const [adminWeeklyPlans, setAdminWeeklyPlans] = useState([])
  const [adminWeeklyStatusFilter, setAdminWeeklyStatusFilter] = useState('pending')
  const [adminWeeklyDecisionById, setAdminWeeklyDecisionById] = useState({})
  const [adminKbReport, setAdminKbReport] = useState(null)
  const [adminBpmItems, setAdminBpmItems] = useState([])
  const [adminMetricsTeam, setAdminMetricsTeam] = useState(null)
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminError, setAdminError] = useState('')
  const [employeeActionLoading, setEmployeeActionLoading] = useState(false)
  const [adminActionLoading, setAdminActionLoading] = useState(false)

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
  const employeeOfficeHoursTotal = useMemo(() => sumShiftHours(employeeWeekDays, 'office'), [employeeWeekDays])
  const employeeOnlineHoursTotal = useMemo(() => sumShiftHours(employeeWeekDays, 'online'), [employeeWeekDays])
  const employeeNeedsReason = employeeOfficeHoursTotal < 24 || employeeOnlineHoursTotal > 16
  const isTeamLead = role === 'TEAMLEAD'
  const isAdminLike = role === 'ADMIN' || role === 'SUPER_ADMIN'

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
    if (landing === 'employee_portal' || landing === 'teamlead_portal') loadEmployeeData()
    if (landing === 'admin_panel') loadAdminData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [landing, token])

  useEffect(() => {
    if (!isTeamLead) return
    const hiddenForTeamLead = ['home', 'my_courses', 'catalog', 'reports']
    if (hiddenForTeamLead.includes(employeeTab)) {
      setEmployeeTab('tasks')
    }
  }, [isTeamLead, employeeTab])

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
      const [homeRes, myRes, catalogRes, reportsRes, scheduleRes, scheduleOptionsRes, structureRes, weeklyPlansRes, tasksMyRes, tasksTeamRes, kbRes, metricsMyRes, metricsTeamRes, bpmRes, bpmTemplatesRes, kbReportRes] = await Promise.all([
        fetch(`${API.accounts}/employee/home/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/my/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/available/`, { headers: authHeaders }),
        fetch(`${API.reports}/employee/daily/`, { headers: authHeaders }),
        fetch(`${API.schedule}/my-schedule/`, { headers: authHeaders }),
        fetch(`${API.schedule}/schedules/`, { headers: authHeaders }),
        fetch(`${API.accounts}/company/structure/`, { headers: authHeaders }),
        fetch(`${API.schedule}/v1/work-schedules/weekly-plans/my/`, { headers: authHeaders }),
        fetch(`${API.tasks}/my/`, { headers: authHeaders }),
        fetch(`${API.tasks}/team/`, { headers: authHeaders }),
        fetch(`${API.kb}/`, { headers: authHeaders }),
        fetch(`${API.metrics}/`, { headers: authHeaders }),
        fetch(`${API.metrics}/team/`, { headers: authHeaders }),
        fetch(`${API.bpm}/`, { headers: authHeaders }),
        fetch(`${API.bpm}/admin/templates/`, { headers: authHeaders }),
        fetch(`${API.kb}/report/`, { headers: authHeaders }),
      ])

      const [
        homeData,
        myData,
        catalogData,
        reportsData,
        scheduleData,
        scheduleOptionsData,
        structureData,
        weeklyPlansData,
        tasksMyData,
        tasksTeamData,
        kbData,
        metricsMyData,
        metricsTeamData,
        bpmData,
        bpmTemplatesData,
        kbReportData,
      ] = await Promise.all([
        toJson(homeRes),
        toJson(myRes),
        toJson(catalogRes),
        toJson(reportsRes),
        toJson(scheduleRes),
        toJson(scheduleOptionsRes),
        toJson(structureRes),
        toJson(weeklyPlansRes),
        toJson(tasksMyRes),
        toJson(tasksTeamRes),
        toJson(kbRes),
        toJson(metricsMyRes),
        toJson(metricsTeamRes),
        toJson(bpmRes),
        toJson(bpmTemplatesRes),
        toJson(kbReportRes),
      ])

      if (!homeRes.ok) throw new Error(getErrorMessage(homeData, 'Не удалось загрузить страницу работника'))
      setEmployeeHome(homeData)
      setEmployeeCoursesMy(Array.isArray(myData) ? myData : [])
      setEmployeeCoursesCatalog(Array.isArray(catalogData) ? catalogData : [])
      setEmployeeReports(Array.isArray(reportsData) ? reportsData : [])
      setEmployeeSchedule(scheduleRes.ok ? scheduleData : null)
      setEmployeeScheduleOptions(scheduleOptionsRes.ok && Array.isArray(scheduleOptionsData) ? scheduleOptionsData : [])
      setCompanyStructure(structureRes.ok ? structureData : null)
      const plans = weeklyPlansRes.ok && Array.isArray(weeklyPlansData) ? weeklyPlansData : []
      setEmployeeWeeklyPlans(plans)
      const selectedWeekStart = pickPlannableWeekStart(plans)
      const selectedWeekPlan = plans.find((item) => item.week_start === selectedWeekStart) || null
      setEmployeeWeekStart(selectedWeekStart)
      setEmployeeWeekDays(createFixedWeekShifts(selectedWeekStart, selectedWeekPlan?.days || []))
      setEmployeeOnlineReason(selectedWeekPlan?.online_reason || '')
      setEmployeeWeekComment(selectedWeekPlan?.employee_comment || '')
      setEmployeeTasksMy(tasksMyRes.ok && Array.isArray(tasksMyData) ? tasksMyData : [])
      setEmployeeTasksTeam(tasksTeamRes.ok && Array.isArray(tasksTeamData) ? tasksTeamData : [])
      setKbArticles(kbRes.ok && Array.isArray(kbData) ? kbData : [])
      setMyMetrics(metricsMyRes.ok ? metricsMyData : null)
      setTeamMetrics(metricsTeamRes.ok ? metricsTeamData : null)
      setBpmItems(bpmRes.ok ? (Array.isArray(bpmData?.items) ? bpmData.items : []) : [])
      setBpmTemplates(bpmTemplatesRes.ok && Array.isArray(bpmTemplatesData) ? bpmTemplatesData : [])
      setKbReport(kbReportRes.ok ? kbReportData : null)
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

  async function submitEmployeeWeeklyPlan(event) {
    event.preventDefault()
    setEmployeeError('')
    const normalizedWeekStart = normalizeWeekStartISO(employeeWeekStart)
    const sanitizedDays = employeeWeekDays
      .map((item) => ({
        date: item.date,
        start_time: item.mode === 'day_off' ? null : item.start_time,
        end_time: item.mode === 'day_off' ? null : item.end_time,
        mode: item.mode,
        comment: item.comment || '',
        breaks:
          item.mode === 'office'
            ? (item.breaks || [])
                .filter((part) => part?.start_time && part?.end_time)
                .map((part) => ({
                  start_time: part.start_time,
                  end_time: part.end_time,
                }))
            : [],
        lunch_start: item.mode === 'office' ? (item.lunch_start || null) : null,
        lunch_end:
          item.mode === 'office' && item.lunch_start
            ? minutesToHHMM((hhmmToMinutes(item.lunch_start) || 0) + 60)
            : null,
      }))
      .filter((item) => item.date && item.mode)

    if (sanitizedDays.length !== 7) {
      setEmployeeError('Нужно заполнить 7 дней (с понедельника по воскресенье).')
      return
    }

    const outsideWeek = sanitizedDays.some((item) => !isShiftInsideWeek(item.date, normalizedWeekStart))
    if (outsideWeek) {
      setEmployeeError('Все смены должны быть внутри выбранной недели (понедельник-воскресенье).')
      return
    }

    const hasInvalidHours = sanitizedDays.some((shift) => {
      if (shift.mode === 'day_off') return false
      const limits = getDayHourLimits(shift.date)
      if (!shift.start_time || !shift.end_time) return true
      return shift.start_time < limits.min || shift.end_time > limits.max || shift.end_time <= shift.start_time
    })
    if (hasInvalidHours) {
      setEmployeeError('Некорректный диапазон времени. Пн-Пт: 09:00-21:00, Сб-Вс: 11:00-19:00, окончание позже начала.')
      return
    }

    const hasInvalidBreakRules = sanitizedDays.some((shift) => {
      if (shift.mode !== 'office') {
        return shift.breaks.length > 0 || shift.lunch_start || shift.lunch_end
      }
      const duration = getShiftHours(shift)
      if (duration < 7 && shift.breaks.length > 0) return true
      if (duration < 8 && (shift.lunch_start || shift.lunch_end)) return true
      if ((shift.lunch_start && !shift.lunch_end) || (!shift.lunch_start && shift.lunch_end)) return true
      if (shift.breaks.length > 4) return true

      const shiftStart = hhmmToMinutes(shift.start_time)
      const shiftEnd = hhmmToMinutes(shift.end_time)
      if (shiftStart === null || shiftEnd === null) return true

      const intervals = []
      for (const part of shift.breaks) {
        const partStart = hhmmToMinutes(part.start_time)
        const partEnd = hhmmToMinutes(part.end_time)
        if (partStart === null || partEnd === null || partEnd <= partStart) return true
        if ((partStart % 15) !== 0 || (partEnd % 15) !== 0) return true
        if ((partEnd - partStart) !== 15) return true
        if (partStart < shiftStart || partEnd > shiftEnd) return true
        intervals.push([partStart, partEnd])
      }

      if (shift.lunch_start && shift.lunch_end) {
        const lunchStart = hhmmToMinutes(shift.lunch_start)
        const lunchEnd = hhmmToMinutes(shift.lunch_end)
        if (lunchStart === null || lunchEnd === null || lunchEnd <= lunchStart) return true
        if ((lunchStart % 15) !== 0 || (lunchEnd % 15) !== 0) return true
        if ((lunchEnd - lunchStart) !== 60) return true
        if (lunchStart < shiftStart || lunchEnd > shiftEnd) return true
        intervals.push([lunchStart, lunchEnd])
      }

      intervals.sort((a, b) => a[0] - b[0])
      for (let i = 1; i < intervals.length; i += 1) {
        if (intervals[i][0] < intervals[i - 1][1]) return true
      }
      return false
    })
    if (hasInvalidBreakRules) {
      setEmployeeError('Неверные правила перерывов/обеда. Перерывы: офис >=7ч, до 4х15м. Обед: офис >=8ч, ровно 60м. Без пересечений.')
      return
    }

    if (employeeNeedsReason && !employeeOnlineReason.trim()) {
      setEmployeeError('Пояснение обязательно, когда офлайн < 24ч и/или онлайн > 16ч.')
      return
    }

    setEmployeeActionLoading(true)
    const res = await fetch(`${API.schedule}/v1/work-schedules/weekly-plans/my/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        week_start: normalizedWeekStart,
        days: sanitizedDays,
        online_reason: employeeOnlineReason,
        employee_comment: employeeWeekComment,
      }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось отправить недельный план работы'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    await loadEmployeeData()
  }

  async function createTeamTask(event) {
    event.preventDefault()
    if (!employeeTaskCreate.title.trim() || !employeeTaskCreate.assignee_id) return
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.tasks}/create/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        title: employeeTaskCreate.title.trim(),
        description: employeeTaskCreate.description || '',
        assignee_id: Number(employeeTaskCreate.assignee_id),
      }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось создать задачу'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeTaskCreate({ title: '', description: '', assignee_id: '' })
    setEmployeeActionLoading(false)
    await loadEmployeeData()
  }

  async function moveTaskColumn() {
    if (!selectedTaskId || !selectedTaskColumn) return
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.tasks}/${selectedTaskId}/move/`, {
      method: 'PATCH',
      headers: authHeaders,
      body: JSON.stringify({ column_id: Number(selectedTaskColumn) }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось переместить задачу'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    await loadEmployeeData()
  }

  async function createBpmInstance(templateId) {
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.bpm}/instances/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ template_id: templateId }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось запустить процесс'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    await loadEmployeeData()
  }

  async function completeBpmStep(stepId) {
    setEmployeeActionLoading(true)
    const res = await fetch(`${API.bpm}/steps/${stepId}/complete/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({}),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setEmployeeError(getErrorMessage(data, 'Не удалось завершить шаг'))
      setEmployeeActionLoading(false)
      return
    }
    setEmployeeActionLoading(false)
    await loadEmployeeData()
  }

  async function loadAdminData() {
    setAdminLoading(true)
    setAdminError('')
    try {
      const [requestsRes, profileRes, notificationsRes, weeklyPlansRes, kbReportRes, bpmListRes, metricsTeamRes] = await Promise.all([
        fetch(`${API.regulations}/admin/intern-requests/?status=pending`, { headers: authHeaders }),
        fetch(`${API.accounts}/me/profile/`, { headers: authHeaders }),
        fetch(`${API.common}/notifications/`, { headers: authHeaders }),
        fetch(`${API.schedule}/v1/work-schedules/admin/weekly-plans/?status=${adminWeeklyStatusFilter}`, { headers: authHeaders }),
        fetch(`${API.kb}/report/`, { headers: authHeaders }),
        fetch(`${API.bpm}/`, { headers: authHeaders }),
        fetch(`${API.metrics}/team/`, { headers: authHeaders }),
      ])
      const [requestsData, profileData, notificationsData, weeklyPlansData, kbReportData, bpmListData, metricsTeamData] = await Promise.all([
        toJson(requestsRes),
        toJson(profileRes),
        toJson(notificationsRes),
        toJson(weeklyPlansRes),
        toJson(kbReportRes),
        toJson(bpmListRes),
        toJson(metricsTeamRes),
      ])
      if (!requestsRes.ok) throw new Error(getErrorMessage(requestsData, 'Не удалось загрузить заявки стажеров'))
      setAdminRequests(Array.isArray(requestsData) ? requestsData : [])

      const departments = profileData?.department ? [{ id: profileData.department_id, name: profileData.department }] : []
      setAdminDepartments(departments)
      setAdminWeeklyPlans(weeklyPlansRes.ok && Array.isArray(weeklyPlansData) ? weeklyPlansData : [])
      setAdminKbReport(kbReportRes.ok ? kbReportData : null)
      setAdminBpmItems(bpmListRes.ok ? (Array.isArray(bpmListData?.items) ? bpmListData.items : []) : [])
      setAdminMetricsTeam(metricsTeamRes.ok ? metricsTeamData : null)

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

  async function refreshAdminWeeklyPlans() {
    setAdminActionLoading(true)
    const res = await fetch(`${API.schedule}/v1/work-schedules/admin/weekly-plans/?status=${adminWeeklyStatusFilter}`, {
      headers: authHeaders,
    })
    const data = await toJson(res)
    if (!res.ok) {
      setAdminError(getErrorMessage(data, 'Не удалось загрузить недельные планы'))
      setAdminActionLoading(false)
      return
    }
    setAdminWeeklyPlans(Array.isArray(data) ? data : [])
    setAdminActionLoading(false)
  }

  async function decideAdminWeeklyPlan(planId) {
    const draft = adminWeeklyDecisionById[planId] || {}
    const action = draft.action || 'approve'
    const admin_comment = draft.admin_comment || ''
    setAdminActionLoading(true)
    const res = await fetch(`${API.schedule}/v1/work-schedules/admin/weekly-plans/${planId}/decision/`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ action, admin_comment }),
    })
    const data = await toJson(res)
    if (!res.ok) {
      setAdminError(getErrorMessage(data, 'Не удалось обработать недельный план'))
      setAdminActionLoading(false)
      return
    }
    setAdminActionLoading(false)
    await refreshAdminWeeklyPlans()
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
        <h2>{isTeamLead ? 'Кабинет тимлида' : 'Кабинет работника'}</h2>
        <p>{employeeHome?.greeting || `Здравствуйте, ${fullName}`}</p>
        {employeeError && <p className="error">{employeeError}</p>}
        {employeeLoading && <p>Загрузка...</p>}

        <nav className="tabs">
          {!isTeamLead && (
            <button className={employeeTab === 'home' ? 'active' : ''} onClick={() => setEmployeeTab('home')}>
              Главная
            </button>
          )}
          {!isTeamLead && (
            <button className={employeeTab === 'my_courses' ? 'active' : ''} onClick={() => setEmployeeTab('my_courses')}>
              Мои курсы
            </button>
          )}
          {!isTeamLead && (
            <button className={employeeTab === 'catalog' ? 'active' : ''} onClick={() => setEmployeeTab('catalog')}>
              Каталог курсов
            </button>
          )}
          {!isTeamLead && (
            <button className={employeeTab === 'reports' ? 'active' : ''} onClick={() => setEmployeeTab('reports')}>
              Отчеты
            </button>
          )}
          <button className={employeeTab === 'schedule' ? 'active' : ''} onClick={() => setEmployeeTab('schedule')}>
            График работы
          </button>
          <button className={employeeTab === 'structure' ? 'active' : ''} onClick={() => setEmployeeTab('structure')}>
            Структура компании
          </button>
                  <button className={employeeTab === 'tasks' ? 'active' : ''} onClick={() => setEmployeeTab('tasks')}>
            Задачи
          </button>
          <button className={employeeTab === 'kb' ? 'active' : ''} onClick={() => setEmployeeTab('kb')}>
            База знаний
          </button>
          <button className={employeeTab === 'metrics' ? 'active' : ''} onClick={() => setEmployeeTab('metrics')}>
            Метрики
          </button>
          <button className={employeeTab === 'bpm' ? 'active' : ''} onClick={() => setEmployeeTab('bpm')}>
            Процессы
          </button></nav>

        {!isTeamLead && employeeTab === 'home' && (
          <div className="card">
            <p>Мои курсы: {employeeHome?.my_courses_count || 0}</p>
            <p>Завершенные курсы: {employeeHome?.completed_courses_count || 0}</p>
            <p>Доступные курсы: {employeeHome?.available_courses_count || 0}</p>
            <p>Ежедневные отчеты: {employeeHome?.daily_reports_count || 0}</p>
          </div>
        )}

        {!isTeamLead && employeeTab === 'my_courses' &&
          employeeCoursesMy.map((item) => (
            <article className="card" key={item.id}>
              <h3>{item.course.title}</h3>
              <p>Статус: {item.status}</p>
              <p>Прогресс: {item.progress_percent}%</p>
            </article>
          ))}

        {!isTeamLead && employeeTab === 'catalog' &&
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

        {!isTeamLead && employeeTab === 'reports' && (
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
          <div>
            <article className="card">
              <h3>Календарь недельного плана</h3>
              <form className="inline-form" onSubmit={submitEmployeeWeeklyPlan}>
                <label>
                  Начало недели (понедельник)
                  <input
                    type="date"
                    value={employeeWeekStart}
                    onChange={(event) => {
                      const nextWeekStart = normalizeWeekStartISO(event.target.value)
                      setEmployeeWeekStart(nextWeekStart)
                      const existingPlan = employeeWeeklyPlans.find((item) => item.week_start === nextWeekStart)
                      setEmployeeWeekDays(createFixedWeekShifts(nextWeekStart, existingPlan?.days || []))
                      setEmployeeOnlineReason(existingPlan?.online_reason || '')
                      setEmployeeWeekComment(existingPlan?.employee_comment || '')
                    }}
                  />
                </label>
                <div className="stats">
                  <span>Офлайн всего: {employeeOfficeHoursTotal}ч</span>
                  <span>Онлайн всего: {employeeOnlineHoursTotal}ч</span>
                </div>
                <div className="week-grid">
                  {employeeWeekDays.map((shift, index) => (
                    <div className="inline-block" key={`${shift.date}-${index}-${shift.mode}`}>
                      <strong>{WEEKDAY_LABELS[index]}</strong>
                      <p className="notice">{shift.date}</p>
                      <label>
                        С
                        <input
                          type="time"
                          step="3600"
                          min={getDayHourLimits(shift.date).min}
                          max={getDayHourLimits(shift.date).max}
                          value={shift.start_time || ''}
                          disabled={shift.mode === 'day_off'}
                          onChange={(event) =>
                            setEmployeeWeekDays((prev) =>
                              prev.map((x, i) =>
                                i === index ? normalizeShiftBreakRules({ ...x, start_time: event.target.value }) : x,
                              ),
                            )
                          }
                        />
                      </label>
                      <label>
                        До
                        <input
                          type="time"
                          step="3600"
                          min={getDayHourLimits(shift.date).min}
                          max={getDayHourLimits(shift.date).max}
                          value={shift.end_time || ''}
                          disabled={shift.mode === 'day_off'}
                          onChange={(event) =>
                            setEmployeeWeekDays((prev) =>
                              prev.map((x, i) =>
                                i === index ? normalizeShiftBreakRules({ ...x, end_time: event.target.value }) : x,
                              ),
                            )
                          }
                        />
                      </label>
                      <label>
                        Режим
                        <select
                          value={shift.mode}
                          onChange={(event) =>
                            setEmployeeWeekDays((prev) =>
                              prev.map((x, i) =>
                                i === index
                                  ? (() => {
                                      const nextMode = event.target.value
                                      if (nextMode === 'day_off') {
                                        return {
                                          ...x,
                                          mode: nextMode,
                                          start_time: '',
                                          end_time: '',
                                          breaks: [],
                                          lunch_start: '',
                                          lunch_end: '',
                                        }
                                      }
                                      const limits = getDayHourLimits(x.date)
                                      if (nextMode === 'online') {
                                        return {
                                          ...x,
                                          mode: nextMode,
                                          start_time: x.start_time || limits.min,
                                          end_time: x.end_time || (index < 5 ? '17:00' : '19:00'),
                                          breaks: [],
                                          lunch_start: '',
                                          lunch_end: '',
                                        }
                                      }
                                      return normalizeShiftBreakRules({
                                        ...x,
                                        mode: nextMode,
                                        start_time: x.start_time || limits.min,
                                        end_time: x.end_time || (index < 5 ? '17:00' : '19:00'),
                                        breaks: Array.isArray(x.breaks) ? x.breaks : [],
                                        lunch_start: x.lunch_start || '',
                                        lunch_end: x.lunch_end || '',
                                      })
                                    })()
                                  : x,
                              ),
                            )
                          }
                        >
                          <option value="office">Офлайн (офис)</option>
                          <option value="online">Онлайн</option>
                          <option value="day_off">Выходной</option>
                        </select>
                      </label>
                      <label>
                        Комментарий к смене
                        <input
                          value={shift.comment}
                          onChange={(event) =>
                            setEmployeeWeekDays((prev) =>
                              prev.map((x, i) => (i === index ? { ...x, comment: event.target.value } : x)),
                            )
                          }
                        />
                      </label>
                      {shift.mode === 'office' && (
                        <div className="breaks-wrap">
                          {canUseShortBreaks(shift) ? (
                            <div className="breaks-list">
                              {(shift.breaks || []).map((part, partIndex) => (
                                <div className="actions-row" key={`${shift.date}-break-${partIndex}`}>
                                  <input
                                    type="time"
                                    step="900"
                                    value={part.start_time || ''}
                                    onChange={(event) =>
                                      setEmployeeWeekDays((prev) =>
                                        prev.map((x, i) =>
                                          i === index
                                            ? {
                                                ...x,
                                                breaks: (x.breaks || []).map((y, yIndex) =>
                                                  yIndex === partIndex
                                                    ? {
                                                        ...y,
                                                        start_time: event.target.value,
                                                        end_time: (() => {
                                                          const startMinutes = hhmmToMinutes(event.target.value)
                                                          return startMinutes === null
                                                            ? y.end_time
                                                            : minutesToHHMM(startMinutes + 15)
                                                        })(),
                                                      }
                                                    : y,
                                                ),
                                              }
                                            : x,
                                        ),
                                      )
                                    }
                                  />
                                  <span>-</span>
                                  <input
                                    type="time"
                                    step="900"
                                    value={part.end_time || ''}
                                    readOnly
                                  />
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setEmployeeWeekDays((prev) =>
                                        prev.map((x, i) =>
                                          i === index
                                            ? {
                                                ...x,
                                                breaks: (x.breaks || []).filter((_, yIndex) => yIndex !== partIndex),
                                              }
                                            : x,
                                        ),
                                      )
                                    }
                                  >
                                    Удалить
                                  </button>
                                </div>
                              ))}
                              <button
                                type="button"
                                disabled={(shift.breaks || []).length >= 4}
                                onClick={() =>
                                  setEmployeeWeekDays((prev) =>
                                    prev.map((x, i) =>
                                      i === index
                                        ? {
                                            ...x,
                                            breaks: [
                                              ...(x.breaks || []),
                                              {
                                                start_time: x.start_time || getDayHourLimits(x.date).min,
                                                end_time: (() => {
                                                  const startMinutes = hhmmToMinutes(x.start_time || getDayHourLimits(x.date).min)
                                                  return startMinutes === null ? '09:15' : minutesToHHMM(startMinutes + 15)
                                                })(),
                                              },
                                            ],
                                          }
                                        : x,
                                    ),
                                  )
                                }
                              >
                                + Добавить перерыв 15 минут
                              </button>
                            </div>
                          ) : null}
                          {canUseLunchBreak(shift) ? (
                            <div className="actions-row">
                              <input
                                type="time"
                                step="900"
                                value={shift.lunch_start || ''}
                                onChange={(event) =>
                                  setEmployeeWeekDays((prev) =>
                                    prev.map((x, i) =>
                                      i === index
                                        ? {
                                            ...x,
                                            lunch_start: event.target.value,
                                            lunch_end: (() => {
                                              const startMinutes = hhmmToMinutes(event.target.value)
                                              return startMinutes === null ? '' : minutesToHHMM(startMinutes + 60)
                                            })(),
                                          }
                                        : x,
                                    ),
                                  )
                                }
                              />
                              <span>-</span>
                              <input
                                type="time"
                                step="900"
                                value={shift.lunch_end || ''}
                                readOnly
                              />
                              <button
                                type="button"
                                onClick={() =>
                                  setEmployeeWeekDays((prev) =>
                                    prev.map((x, i) =>
                                      i === index ? { ...x, lunch_start: '', lunch_end: '' } : x,
                                    ),
                                  )
                                }
                              >
                                Очистить обед
                              </button>
                            </div>
                          ) : null}
                        </div>
                      )}
                      <p>Часы: {shift.mode === 'day_off' ? '-' : `${getShiftHours(shift)}ч`}</p>
                    </div>
                  ))}
                </div>
                <label>
                  Пояснение (обязательно, если офлайн {'<'} 24ч и/или онлайн {'>'} 16ч)
                  <textarea
                    value={employeeOnlineReason}
                    required={employeeNeedsReason}
                    onChange={(event) => setEmployeeOnlineReason(event.target.value)}
                  />
                </label>
                <label>
                  Комментарий сотрудника
                  <textarea value={employeeWeekComment} onChange={(event) => setEmployeeWeekComment(event.target.value)} />
                </label>
                <button type="submit" disabled={employeeActionLoading}>
                  {employeeActionLoading ? 'Отправка...' : 'Отправить на согласование администратору'}
                </button>
              </form>
            </article>

            <article className="card">
              <h3>Мои недельные планы</h3>
              {employeeWeeklyPlans.length === 0 && <p>Недельных планов пока нет.</p>}
              {employeeWeeklyPlans.map((plan) => (
                <div key={plan.id} className="inline-block">
                  <p>Неделя: {plan.week_start}</p>
                  <p>Статус: {plan.status}</p>
                  <p>Офис: {plan.office_hours}ч, Онлайн: {plan.online_hours}ч</p>
                  {Array.isArray(plan.days) && (
                    <div className="week-grid">
                      {plan.days.map((shift, idx) => (
                        <div className="inline-block" key={`${plan.id}-shift-${idx}`}>
                          <p>{shift.date} ({formatShiftWeekday(shift.date)})</p>
                          <p>{shift.mode === 'day_off' ? 'Выходной' : `${shift.start_time} - ${shift.end_time}`}</p>
                          <p>Режим: {shift.mode}</p>
                          {Array.isArray(shift.breaks) && shift.breaks.length > 0 ? (
                            <p>Перерывы: {shift.breaks.map((part) => `${part.start_time}-${part.end_time}`).join(', ')}</p>
                          ) : null}
                          {shift.lunch_start && shift.lunch_end ? <p>Обед: {shift.lunch_start}-{shift.lunch_end}</p> : null}
                          {shift.comment ? <p>Комментарий: {shift.comment}</p> : null}
                        </div>
                      ))}
                    </div>
                  )}
                  {plan.admin_comment ? <p>Комментарий администратора: {plan.admin_comment}</p> : null}
                </div>
              ))}
            </article>
          </div>
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

        {employeeTab === 'tasks' && (
          <div>
            {(isTeamLead || isAdminLike) && (
              <article className="card">
                <h3>Создать задачу для команды</h3>
                <form className="inline-form" onSubmit={createTeamTask}>
                  <input
                    placeholder="Название"
                    value={employeeTaskCreate.title}
                    onChange={(event) => setEmployeeTaskCreate((prev) => ({ ...prev, title: event.target.value }))}
                  />
                  <textarea
                    placeholder="Описание"
                    value={employeeTaskCreate.description}
                    onChange={(event) => setEmployeeTaskCreate((prev) => ({ ...prev, description: event.target.value }))}
                  />
                  <input
                    type="number"
                    placeholder="ID исполнителя"
                    value={employeeTaskCreate.assignee_id}
                    onChange={(event) => setEmployeeTaskCreate((prev) => ({ ...prev, assignee_id: event.target.value }))}
                  />
                  <button type="submit" disabled={employeeActionLoading}>Создать задачу</button>
                </form>
              </article>
            )}
            <article className="card">
              <h3>Мои задачи</h3>
              {employeeTasksMy.length === 0 && <p>Задач пока нет.</p>}
              {employeeTasksMy.map((task) => (
                <div className="inline-block" key={task.id}>
                  <p><strong>{task.title}</strong></p>
                  <p>Колонка: {task.column}</p>
                  <p>Приоритет: {task.priority}</p>
                  <p>Срок: {task.due_date || '-'}</p>
                </div>
              ))}
            </article>
            {(isTeamLead || isAdminLike) && (
              <article className="card">
                <h3>Задачи команды</h3>
                {employeeTasksTeam.length === 0 && <p>У команды пока нет задач.</p>}
                {employeeTasksTeam.map((task) => (
                  <div className="inline-block" key={task.id}>
                    <p><strong>{task.title}</strong></p>
                    <p>Исполнитель: {task.assignee_username}</p>
                    <p>Колонка: {task.column}</p>
                  </div>
                ))}
                <div className="actions-row">
                  <input type="number" placeholder="ID задачи" value={selectedTaskId} onChange={(event) => setSelectedTaskId(event.target.value)} />
                  <input type="number" placeholder="ID колонки" value={selectedTaskColumn} onChange={(event) => setSelectedTaskColumn(event.target.value)} />
                  <button disabled={employeeActionLoading} onClick={moveTaskColumn}>Переместить задачу</button>
                </div>
              </article>
            )}
          </div>
        )}

        {employeeTab === 'kb' && (
          <div>
            <article className="card">
              <h3>Статьи базы знаний</h3>
              {kbArticles.length === 0 && <p>Статей пока нет.</p>}
              {kbArticles.map((article) => (
                <div className="inline-block" key={article.id}>
                  <p><strong>{article.title}</strong></p>
                  <p>Видимость: {article.visibility}</p>
                  <p>Категория: {article.category_name || '-'}</p>
                </div>
              ))}
            </article>
            {(isTeamLead || isAdminLike) && kbReport && (
              <article className="card">
                <h3>Отчет по базе знаний (30 дней)</h3>
                {(kbReport.top_30_days || []).map((row) => (
                  <div className="inline-block" key={row.article_id}>
                    <p><strong>{row.title}</strong></p>
                    <p>Просмотры: {row.views}</p>
                    <p>Уникальные: {row.unique_views}</p>
                    <p>Охват: {row.view_percent}%</p>
                  </div>
                ))}
              </article>
            )}
          </div>
        )}

        {employeeTab === 'metrics' && (
          <div>
            <article className="card">
              <h3>Мои метрики</h3>
              {!myMetrics && <p>Данных пока нет.</p>}
              {myMetrics && (
                <div className="stats">
                  <span>Создано за 7 дней: {myMetrics.tasks_created_7d}</span>
                  <span>Закрыто за 7 дней: {myMetrics.tasks_closed_7d}</span>
                  <span>Просрочено: {myMetrics.tasks_overdue}</span>
                  <span>Посещаемость: {myMetrics.attendance_percent_month}%</span>
                  <span>Просмотры БЗ: {myMetrics.kb_views_month}</span>
                </div>
              )}
            </article>
            {(isTeamLead || isAdminLike) && (
              <article className="card">
                <h3>Метрики команды</h3>
                {!teamMetrics && <p>Данных по команде пока нет.</p>}
                {teamMetrics && (
                  <div className="stats">
                    <span>Размер команды: {teamMetrics.team_size}</span>
                    <span>Создано за 7 дней: {teamMetrics.tasks_created_7d}</span>
                    <span>Закрыто за 7 дней: {teamMetrics.tasks_closed_7d}</span>
                    <span>Просрочено: {teamMetrics.tasks_overdue}</span>
                    <span>Посещаемость: {teamMetrics.attendance_percent_month}%</span>
                  </div>
                )}
              </article>
            )}
          </div>
        )}

        {employeeTab === 'bpm' && (
          <div>
            <article className="card">
              <h3>Процессы</h3>
              {bpmItems.length === 0 && <p>Активных процессов нет.</p>}
              {bpmItems.map((item) => (
                <div className="inline-block" key={item.id}>
                  <p><strong>{item.template_name}</strong></p>
                  <p>Статус: {item.status}</p>
                  {(item.steps || []).map((step) => (
                    <div className="actions-row" key={step.id}>
                      <span>#{step.order} {step.step_name} ({step.status})</span>
                      {step.status === 'in_progress' && <button onClick={() => completeBpmStep(step.id)}>Завершить шаг</button>}
                    </div>
                  ))}
                </div>
              ))}
            </article>
            <article className="card">
              <h3>Запуск процесса</h3>
              {(bpmTemplates || []).length === 0 && <p>Нет доступных шаблонов.</p>}
              {(bpmTemplates || []).map((template) => (
                <div className="actions-row" key={template.id}>
                  <span>{template.name}</span>
                  <button onClick={() => createBpmInstance(template.id)}>Запустить</button>
                </div>
              ))}
            </article>
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

        <h3>Недельные планы сотрудников</h3>
        <article className="card">
          <div className="actions-row">
            <label>
              Фильтр по статусу
              <select
                value={adminWeeklyStatusFilter}
                onChange={(event) => setAdminWeeklyStatusFilter(event.target.value)}
              >
                <option value="pending">Ожидает</option>
                <option value="clarification_requested">Требует уточнений</option>
                <option value="approved">Одобрен</option>
                <option value="rejected">Отклонен</option>
              </select>
            </label>
            <button onClick={refreshAdminWeeklyPlans} disabled={adminActionLoading}>
              {adminActionLoading ? 'Загрузка...' : 'Обновить'}
            </button>
          </div>
        </article>
        {adminWeeklyPlans.length === 0 && <p>Для выбранного статуса заявок нет.</p>}
        {adminWeeklyPlans.map((plan) => (
          <article className="card" key={plan.id}>
            <p>Сотрудник: {plan.username}</p>
            <p>Неделя: {plan.week_start}</p>
            <p>Офис: {plan.office_hours}ч, Онлайн: {plan.online_hours}ч</p>
            {Array.isArray(plan.days) && (
              <div className="week-grid">
                {plan.days.map((shift, idx) => (
                  <div className="inline-block" key={`${plan.id}-${idx}`}>
                    <p>{shift.date} ({formatShiftWeekday(shift.date)})</p>
                    <p>{shift.mode === 'day_off' ? 'Выходной' : `${shift.start_time} - ${shift.end_time}`}</p>
                    <p>Режим: {shift.mode}</p>
                    {Array.isArray(shift.breaks) && shift.breaks.length > 0 ? (
                      <p>Перерывы: {shift.breaks.map((part) => `${part.start_time}-${part.end_time}`).join(', ')}</p>
                    ) : null}
                    {shift.lunch_start && shift.lunch_end ? <p>Обед: {shift.lunch_start}-{shift.lunch_end}</p> : null}
                    {shift.comment ? <p>Комментарий: {shift.comment}</p> : null}
                  </div>
                ))}
              </div>
            )}
            {plan.online_reason ? <p>Причина онлайна: {plan.online_reason}</p> : null}
            <div className="actions-row">
              <select
                value={adminWeeklyDecisionById[plan.id]?.action || 'approve'}
                onChange={(event) =>
                  setAdminWeeklyDecisionById((prev) => ({
                    ...prev,
                    [plan.id]: { ...(prev[plan.id] || {}), action: event.target.value },
                  }))
                }
              >
                <option value="approve">Одобрить</option>
                <option value="request_clarification">Запросить уточнение</option>
                <option value="reject">Отклонить</option>
              </select>
              <input
                placeholder="Комментарий администратора"
                value={adminWeeklyDecisionById[plan.id]?.admin_comment || ''}
                onChange={(event) =>
                  setAdminWeeklyDecisionById((prev) => ({
                    ...prev,
                    [plan.id]: { ...(prev[plan.id] || {}), admin_comment: event.target.value },
                  }))
                }
              />
              <button disabled={adminActionLoading} onClick={() => decideAdminWeeklyPlan(plan.id)}>
                Отправить решение
              </button>
            </div>
          </article>
        ))}

        <h3>Метрики команды</h3>
        <article className="card">
          {!adminMetricsTeam && <p>Данных по команде пока нет.</p>}
          {adminMetricsTeam && (
            <div className="stats">
              <span>Размер команды: {adminMetricsTeam.team_size}</span>
              <span>Создано за 7 дней: {adminMetricsTeam.tasks_created_7d}</span>
              <span>Закрыто за 7 дней: {adminMetricsTeam.tasks_closed_7d}</span>
              <span>Просрочено: {adminMetricsTeam.tasks_overdue}</span>
              <span>Посещаемость: {adminMetricsTeam.attendance_percent_month}%</span>
            </div>
          )}
        </article>

        <h3>Отчет по базе знаний (30 дней)</h3>
        <article className="card">
          {!adminKbReport && <p>Данных по базе знаний пока нет.</p>}
          {(adminKbReport?.top_30_days || []).map((row) => (
            <div className="inline-block" key={`admin-kb-${row.article_id}`}>
              <p><strong>{row.title}</strong></p>
              <p>Просмотры: {row.views}</p>
              <p>Уникальные: {row.unique_views}</p>
              <p>Охват: {row.view_percent}%</p>
            </div>
          ))}
        </article>

        <h3>Инстансы процессов</h3>
        <article className="card">
          {adminBpmItems.length === 0 && <p>Активных инстансов процессов нет.</p>}
          {adminBpmItems.map((item) => (
            <div className="inline-block" key={`admin-bpm-${item.id}`}>
              <p><strong>{item.template_name}</strong></p>
              <p>Статус: {item.status}</p>
              <p>Запустил: {item.started_by_username || '-'}</p>
            </div>
          ))}
        </article>
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
      {token && landing === 'teamlead_portal' && renderEmployeePortal()}
      {token && landing === 'admin_panel' && renderAdminPortal()}
    </main>
  )
}

export default App








