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
const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

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

  const [adminRequests, setAdminRequests] = useState([])
  const [adminDepartments, setAdminDepartments] = useState([])
  const [adminWeeklyPlans, setAdminWeeklyPlans] = useState([])
  const [adminWeeklyStatusFilter, setAdminWeeklyStatusFilter] = useState('pending')
  const [adminWeeklyDecisionById, setAdminWeeklyDecisionById] = useState({})
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
      const [homeRes, myRes, catalogRes, reportsRes, scheduleRes, scheduleOptionsRes, structureRes, weeklyPlansRes] = await Promise.all([
        fetch(`${API.accounts}/employee/home/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/my/`, { headers: authHeaders }),
        fetch(`${API.content}/courses/available/`, { headers: authHeaders }),
        fetch(`${API.reports}/employee/daily/`, { headers: authHeaders }),
        fetch(`${API.schedule}/my-schedule/`, { headers: authHeaders }),
        fetch(`${API.schedule}/schedules/`, { headers: authHeaders }),
        fetch(`${API.accounts}/company/structure/`, { headers: authHeaders }),
        fetch(`${API.schedule}/v1/work-schedules/weekly-plans/my/`, { headers: authHeaders }),
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
      ] = await Promise.all([
        toJson(homeRes),
        toJson(myRes),
        toJson(catalogRes),
        toJson(reportsRes),
        toJson(scheduleRes),
        toJson(scheduleOptionsRes),
        toJson(structureRes),
        toJson(weeklyPlansRes),
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
      setEmployeeError('Need 7 day entries (Monday through Sunday).')
      return
    }

    const outsideWeek = sanitizedDays.some((item) => !isShiftInsideWeek(item.date, normalizedWeekStart))
    if (outsideWeek) {
      setEmployeeError('All shifts must be inside the selected week (Monday-Sunday).')
      return
    }

    const hasInvalidHours = sanitizedDays.some((shift) => {
      if (shift.mode === 'day_off') return false
      const limits = getDayHourLimits(shift.date)
      if (!shift.start_time || !shift.end_time) return true
      return shift.start_time < limits.min || shift.end_time > limits.max || shift.end_time <= shift.start_time
    })
    if (hasInvalidHours) {
      setEmployeeError('Invalid time range. Mon-Fri: 09:00-21:00, Sat-Sun: 11:00-19:00, and end must be after start.')
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
      setEmployeeError('Break/lunch rules are invalid. Breaks: office >=7h, up to 4x15m. Lunch: office >=8h, exactly 60m. No overlaps.')
      return
    }

    if (employeeNeedsReason && !employeeOnlineReason.trim()) {
      setEmployeeError('Explanation is required when offline < 24h and/or online > 16h.')
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
      setEmployeeError(getErrorMessage(data, 'Failed to submit weekly work plan'))
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
      const [requestsRes, profileRes, notificationsRes, weeklyPlansRes] = await Promise.all([
        fetch(`${API.regulations}/admin/intern-requests/?status=pending`, { headers: authHeaders }),
        fetch(`${API.accounts}/me/profile/`, { headers: authHeaders }),
        fetch(`${API.common}/notifications/`, { headers: authHeaders }),
        fetch(`${API.schedule}/v1/work-schedules/admin/weekly-plans/?status=${adminWeeklyStatusFilter}`, { headers: authHeaders }),
      ])
      const [requestsData, profileData, notificationsData, weeklyPlansData] = await Promise.all([
        toJson(requestsRes),
        toJson(profileRes),
        toJson(notificationsRes),
        toJson(weeklyPlansRes),
      ])
      if (!requestsRes.ok) throw new Error(getErrorMessage(requestsData, 'Не удалось загрузить заявки стажеров'))
      setAdminRequests(Array.isArray(requestsData) ? requestsData : [])

      const departments = profileData?.department ? [{ id: profileData.department_id, name: profileData.department }] : []
      setAdminDepartments(departments)
      setAdminWeeklyPlans(weeklyPlansRes.ok && Array.isArray(weeklyPlansData) ? weeklyPlansData : [])

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
      setAdminError(getErrorMessage(data, 'Failed to load weekly plans'))
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
      setAdminError(getErrorMessage(data, 'Failed to process weekly plan'))
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
          <div>
            <article className="card">
              <h3>Weekly plan calendar</h3>
              <form className="inline-form" onSubmit={submitEmployeeWeeklyPlan}>
                <label>
                  Week start (Monday)
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
                  <span>Offline total: {employeeOfficeHoursTotal}h</span>
                  <span>Online total: {employeeOnlineHoursTotal}h</span>
                </div>
                <div className="week-grid">
                  {employeeWeekDays.map((shift, index) => (
                    <div className="inline-block" key={`${shift.date}-${index}-${shift.mode}`}>
                      <strong>{WEEKDAY_LABELS[index]}</strong>
                      <p className="notice">{shift.date}</p>
                      <label>
                        From
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
                        To
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
                        Mode
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
                          <option value="office">Offline (office)</option>
                          <option value="online">Online</option>
                          <option value="day_off">Day off</option>
                        </select>
                      </label>
                      <label>
                        Shift comment
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
                                    Remove
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
                                + Add 15-minute break
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
                                Clear lunch
                              </button>
                            </div>
                          ) : null}
                        </div>
                      )}
                      <p>Hours: {shift.mode === 'day_off' ? '-' : `${getShiftHours(shift)}h`}</p>
                    </div>
                  ))}
                </div>
                <label>
                  Explanation (required when offline {'<'} 24h and/or online {'>'} 16h)
                  <textarea
                    value={employeeOnlineReason}
                    required={employeeNeedsReason}
                    onChange={(event) => setEmployeeOnlineReason(event.target.value)}
                  />
                </label>
                <label>
                  Employee comment
                  <textarea value={employeeWeekComment} onChange={(event) => setEmployeeWeekComment(event.target.value)} />
                </label>
                <button type="submit" disabled={employeeActionLoading}>
                  {employeeActionLoading ? 'Submitting...' : 'Send for admin approval'}
                </button>
              </form>
            </article>

            <article className="card">
              <h3>My weekly plans</h3>
              {employeeWeeklyPlans.length === 0 && <p>No weekly plans yet.</p>}
              {employeeWeeklyPlans.map((plan) => (
                <div key={plan.id} className="inline-block">
                  <p>Week: {plan.week_start}</p>
                  <p>Status: {plan.status}</p>
                  <p>Office: {plan.office_hours}h, Online: {plan.online_hours}h</p>
                  {Array.isArray(plan.days) && (
                    <div className="week-grid">
                      {plan.days.map((shift, idx) => (
                        <div className="inline-block" key={`${plan.id}-shift-${idx}`}>
                          <p>{shift.date} ({formatShiftWeekday(shift.date)})</p>
                          <p>{shift.mode === 'day_off' ? 'Day off' : `${shift.start_time} - ${shift.end_time}`}</p>
                          <p>Mode: {shift.mode}</p>
                          {Array.isArray(shift.breaks) && shift.breaks.length > 0 ? (
                            <p>Breaks: {shift.breaks.map((part) => `${part.start_time}-${part.end_time}`).join(', ')}</p>
                          ) : null}
                          {shift.lunch_start && shift.lunch_end ? <p>Lunch: {shift.lunch_start}-{shift.lunch_end}</p> : null}
                          {shift.comment ? <p>Comment: {shift.comment}</p> : null}
                        </div>
                      ))}
                    </div>
                  )}
                  {plan.admin_comment ? <p>Admin comment: {plan.admin_comment}</p> : null}
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

        <h3>Weekly plans from employees</h3>
        <article className="card">
          <div className="actions-row">
            <label>
              Status filter
              <select
                value={adminWeeklyStatusFilter}
                onChange={(event) => setAdminWeeklyStatusFilter(event.target.value)}
              >
                <option value="pending">pending</option>
                <option value="clarification_requested">clarification_requested</option>
                <option value="approved">approved</option>
                <option value="rejected">rejected</option>
              </select>
            </label>
            <button onClick={refreshAdminWeeklyPlans} disabled={adminActionLoading}>
              {adminActionLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </article>
        {adminWeeklyPlans.length === 0 && <p>No weekly plans for selected status.</p>}
        {adminWeeklyPlans.map((plan) => (
          <article className="card" key={plan.id}>
            <p>User: {plan.username}</p>
            <p>Week: {plan.week_start}</p>
            <p>Office: {plan.office_hours}h, Online: {plan.online_hours}h</p>
            {Array.isArray(plan.days) && (
              <div className="week-grid">
                {plan.days.map((shift, idx) => (
                  <div className="inline-block" key={`${plan.id}-${idx}`}>
                    <p>{shift.date} ({formatShiftWeekday(shift.date)})</p>
                    <p>{shift.mode === 'day_off' ? 'Day off' : `${shift.start_time} - ${shift.end_time}`}</p>
                    <p>Mode: {shift.mode}</p>
                    {Array.isArray(shift.breaks) && shift.breaks.length > 0 ? (
                      <p>Breaks: {shift.breaks.map((part) => `${part.start_time}-${part.end_time}`).join(', ')}</p>
                    ) : null}
                    {shift.lunch_start && shift.lunch_end ? <p>Lunch: {shift.lunch_start}-{shift.lunch_end}</p> : null}
                    {shift.comment ? <p>Comment: {shift.comment}</p> : null}
                  </div>
                ))}
              </div>
            )}
            {plan.online_reason ? <p>Online reason: {plan.online_reason}</p> : null}
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
                <option value="approve">approve</option>
                <option value="request_clarification">request_clarification</option>
                <option value="reject">reject</option>
              </select>
              <input
                placeholder="Admin comment"
                value={adminWeeklyDecisionById[plan.id]?.admin_comment || ''}
                onChange={(event) =>
                  setAdminWeeklyDecisionById((prev) => ({
                    ...prev,
                    [plan.id]: { ...(prev[plan.id] || {}), admin_comment: event.target.value },
                  }))
                }
              />
              <button disabled={adminActionLoading} onClick={() => decideAdminWeeklyPlan(plan.id)}>
                Submit decision
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






