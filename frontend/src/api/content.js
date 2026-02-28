import api from './axios';

export const newsAPI = {
  list: () => api.get('/core/news/'),
  create: (data) => api.post('/core/news/', data),
  update: (id, data) => api.patch(`/core/news/${id}/`, data),
  delete: (id) => api.delete(`/core/news/${id}/`),
};

export const regulationsAPI = {
  list: (params) => api.get('/content/regulations/', { params }),
  create: (data) => api.post('/content/regulations/', data),
  update: (id, data) => api.patch(`/content/regulations/${id}/`, data),
  delete: (id) => api.delete(`/content/regulations/${id}/`),
};

export const instructionsAPI = {
  list: () => api.get('/content/instructions/'),
};

export const onboardingAPI = {
  getMy: () => api.get('/onboarding/my/'),
  listDays: () => api.get('/v1/onboarding/days/'),
  getDay: (id) => api.get(`/v1/onboarding/days/${id}/`),
  completeDay: (id) => api.post(`/v1/onboarding/days/${id}/complete/`),
  submitReport: (data) => api.post('/onboarding/reports/', data),
  updateReport: (id, data) => api.patch(`/onboarding/reports/${id}/`, data),
  getReports: (params) => api.get('/onboarding/reports/', { params }),
  reviewReport: (id, data) => api.post(`/onboarding/reports/${id}/review/`, data),
};

export const schedulesAPI = {
  getWorkSchedules: () => api.get('/schedules/work-schedules/'),
  getMine: () => api.get('/schedules/user-schedules/mine/'),
  getHolidays: (year) => api.get('/schedules/holidays/', { params: { year } }),
  select: (scheduleId) => api.post('/v1/work-schedules/select/', { schedule_id: scheduleId }),
  weeklyPlanSubmit: (data) => api.post('/v1/work-schedules/weekly-plans/my/', data),
  adminTemplates: () => api.get('/v1/work-schedules/admin/templates/'),
  adminCreateTemplate: (data) => api.post('/v1/work-schedules/admin/templates/', data),
  adminUpdateTemplate: (id, data) => api.patch(`/v1/work-schedules/admin/templates/${id}/`, data),
  adminRequests: (params) => api.get('/v1/work-schedules/admin/requests/', { params }),
  adminRequestDecision: (id, approved) => api.post(`/v1/work-schedules/admin/requests/${id}/decision/`, { approved }),
  adminAssign: (data) => api.post('/v1/work-schedules/admin/assign/', data),
  weeklyPlansMy: () => api.get('/v1/work-schedules/weekly-plans/my/'),
  weeklyPlansAdmin: (params) => api.get('/v1/work-schedules/admin/weekly-plans/', { params }),
  weeklyPlanDecision: (id, data) => api.post(`/v1/work-schedules/admin/weekly-plans/${id}/decision/`, data),
};

export const feedbackAPI = {
  list: () => api.get('/feedback/tickets/'),
  create: (data) => api.post('/feedback/tickets/', data),
  reply: (id, data) => api.post(`/feedback/tickets/${id}/reply/`, data),
};

export const auditAPI = {
  list: (params) => api.get('/core/audit/', { params }),
};

export const tasksAPI = {
  my: () => api.get('/v1/tasks/my/'),
  team: () => api.get('/v1/tasks/team/'),
  create: (data) => api.post('/v1/tasks/create/', data),
  detail: (id) => api.get(`/v1/tasks/${id}/`),
  update: (id, data) => api.patch(`/v1/tasks/${id}/`, data),
};

export const companyAPI = {
  structure: () => api.get('/v1/accounts/company/structure/'),
  org: (params) => api.get('/v1/accounts/org/structure/', { params }),
};

export const payrollAPI = {
  my: (params) => api.get('/v1/payroll/', { params }),
  adminList: (params) => api.get('/v1/payroll/admin/', { params }),
  generate: (data) => api.post('/v1/payroll/admin/generate/', data),
  salaryProfiles: () => api.get('/v1/payroll/admin/salary-profiles/'),
  createSalaryProfile: (data) => api.post('/v1/payroll/admin/salary-profiles/', data),
  updateSalaryProfile: (id, data) => api.patch(`/v1/payroll/admin/salary-profiles/${id}/`, data),
};
