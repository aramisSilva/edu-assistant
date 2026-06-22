export type Profile = {
  course_name: string;
  semester: number;
  pole_name: string;
  weekly_hours?: number;
  focus?: string;
  study_disciplines: string[];
};

export type Task = {
  id: number;
  title: string;
  discipline?: string;
  due_date: string;
  status: "PENDING" | "DONE";
  notes?: string;
  source: "manual" | "moodle";
  deadline: { code: string; label: string; days_left: number; severity: number };
};

export type Course = { external_id: string; shortname?: string; fullname: string };
export type Conversation = { id: number; title: string; updated_at: string };
export type Message = { role: "user" | "assistant"; content: string; topic?: string };

export type AppNotification = {
  id: number;
  type: "course" | "task" | "deadline" | "sync";
  severity: "info" | "warning" | "urgent";
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  related_kind?: string;
  related_id?: string;
  action_url?: string;
};

export type AvailabilitySlot = {
  weekday: number;
  start_time: string;
  end_time: string;
};

export type StudyBlock = {
  id: number;
  task_id?: number;
  title: string;
  discipline?: string;
  study_date: string;
  start_time: string;
  duration_minutes: 30 | 60 | 90;
  origin: "suggested" | "manual";
  status: "planned" | "completed";
  task_due_date?: string;
  task_source?: "manual" | "moodle";
};

export type AgendaSuggestion = Omit<StudyBlock, "id" | "status"> & {
  reason: string;
  task_due_date: string;
  task_source: "manual" | "moodle";
};

export type MoodleDiagnostics = {
  status: "ok" | "warning" | "error";
  base_url: string;
  token_configured: boolean;
  moodle_available: boolean;
  user: { id: number; username?: string; fullname?: string } | null;
  courses_count: number;
  last_sync: { moodle_user_id: number; moodle_username?: string; last_synced_at: string } | null;
  message: string;
  checks: Array<{ label: string; status: "ok" | "warning" | "error"; detail: string }>;
};

export type Insights = {
  progress: {
    total_questions: number;
    active_topics: number;
    pending_tasks: number;
    completed_tasks: number;
    moodle_courses: number;
    due_soon: number;
    overdue: number;
  };
  topics: Array<{ topic: string; count: number; percent: number }>;
  recommendations: Array<{ title: string; priority: string; description: string }>;
  recommendation: string;
};

export type ChatContext = {
  profile: Profile | null;
  courses: Course[];
  upcoming_tasks: Task[];
  topics: Array<{ topic: string; count: number }>;
  sync_state: { moodle_user_id: number; moodle_username?: string; last_synced_at: string } | null;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Não foi possível concluir a operação.");
  return data;
}

export const api = {
  bootstrap: () => request<any>("/bootstrap"),
  profile: () => request<{ profile: Profile | null }>("/profile"),
  saveProfile: (profile: Profile) => request<{ profile: Profile }>("/profile", { method: "PUT", body: JSON.stringify(profile) }),
  dashboard: () => request<any>("/dashboard"),
  moodleDiagnostics: () => request<MoodleDiagnostics>("/moodle/diagnostics"),
  syncMoodle: () => request<{ courses: number; tasks: number; notifications_created: number }>("/moodle/sync", { method: "POST" }),
  todayPlan: () => request<{ text: string }>("/dashboard/today-plan", { method: "POST" }),
  suggestion: () => request<{ text: string }>("/dashboard/suggestion", { method: "POST" }),
  tasks: () => request<{ tasks: Task[] }>("/tasks"),
  createTask: (task: Partial<Task>) => request<{ tasks: Task[] }>("/tasks", { method: "POST", body: JSON.stringify(task) }),
  setTaskStatus: (id: number, status: "PENDING" | "DONE") => request<{ tasks: Task[] }>(`/tasks/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  conversations: () => request<{ conversations: Conversation[] }>("/conversations"),
  createConversation: () => request<{ id: number; conversations: Conversation[] }>("/conversations", { method: "POST", body: JSON.stringify({}) }),
  deleteConversation: (id: number) => request<{ conversations: Conversation[] }>(`/conversations/${id}`, { method: "DELETE" }),
  chatContext: () => request<ChatContext>("/chat/context"),
  messages: (id: number) => request<{ messages: Message[] }>(`/conversations/${id}/messages`),
  sendMessage: (id: number, content: string) => request(`/conversations/${id}/messages`, { method: "POST", body: JSON.stringify({ content }) }),
  insights: () => request<Insights>("/insights"),
  notifications: (status = "all") => request<{ notifications: AppNotification[] }>(`/notifications?status=${status}`),
  notificationSummary: () => request<{ unread_count: number; notifications: AppNotification[] }>("/notifications/summary"),
  markNotificationRead: (id: number) => request<{ unread_count: number; changed: number }>(`/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () => request<{ unread_count: number; changed: number }>("/notifications/read-all", { method: "POST" }),
  deleteReadNotifications: () => request<{ unread_count: number; changed: number }>("/notifications/read", { method: "DELETE" }),
  availability: () => request<{ availability: AvailabilitySlot[] }>("/agenda/availability"),
  saveAvailability: (availability: AvailabilitySlot[]) => request<{ availability: AvailabilitySlot[] }>("/agenda/availability", { method: "PUT", body: JSON.stringify(availability) }),
  agenda: (dateFrom: string, dateTo: string) => request<{ blocks: StudyBlock[] }>(`/agenda?date_from=${dateFrom}&date_to=${dateTo}`),
  agendaSuggestions: (startDate?: string) => request<{ suggestions: AgendaSuggestion[] }>("/agenda/suggestions", { method: "POST", body: JSON.stringify({ start_date: startDate }) }),
  createStudyBlocks: (blocks: AgendaSuggestion[]) => request<{ blocks: StudyBlock[] }>("/agenda/blocks", { method: "POST", body: JSON.stringify({ blocks }) }),
  completeStudyBlock: (id: number) => request<{ blocks: StudyBlock[] }>(`/agenda/blocks/${id}/complete`, { method: "PATCH" }),
  rescheduleStudyBlock: (id: number, payload: { study_date: string; start_time: string; duration_minutes: 30 | 60 | 90 }) => request<{ blocks: StudyBlock[] }>(`/agenda/blocks/${id}/reschedule`, { method: "PATCH", body: JSON.stringify(payload) }),
};
