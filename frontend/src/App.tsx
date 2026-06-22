import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import {
  api,
  type AgendaSuggestion,
  type AppNotification,
  type AvailabilitySlot,
  type ChatContext,
  type Conversation,
  type Insights as InsightsData,
  type Message,
  type MoodleDiagnostics,
  type Profile,
  type StudyBlock,
  type Task,
} from "./api";
import {
  AlertCircle,
  Bell,
  BookOpen,
  CalendarClock,
  CalendarDays,
  CheckCircle2,
  CircleUserRound,
  GraduationCap,
  LayoutDashboard,
  Lightbulb,
  MessageCircle,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
  TrendingUp,
} from "lucide-react";

const defaultProfile: Profile = {
  course_name: "Bacharelado Interdisciplinar em Ciência e Tecnologia (BICT) - UFMT",
  semester: 1,
  pole_name: "Cuiabá",
  weekly_hours: 5,
  focus: "",
  study_disciplines: [],
};

const fmt = (date?: string) =>
  date ? new Date(`${date.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR") : "-";

const fmtDateTime = (date?: string) => (date ? new Date(date).toLocaleString("pt-BR") : "Ainda não sincronizado");
const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};
const addDays = (value: Date, days: number) => {
  const result = new Date(value);
  result.setDate(result.getDate() + days);
  return result;
};
const startOfWeek = (value = new Date()) => {
  const result = new Date(value);
  const weekday = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - weekday);
  result.setHours(12, 0, 0, 0);
  return result;
};

function useLoad<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const reload = async () => {
    try {
      setError("");
      setData(await loader());
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    void reload();
  }, deps);
  return { data, error, reload };
}

function Alert({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div className={`rounded-xl px-4 py-3 text-sm ${error ? "bg-red-50 text-red-700" : "bg-brand-50 text-brand-700"}`}>
      {children}
    </div>
  );
}

function Welcome() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#d7efe8,transparent_35%),linear-gradient(135deg,#f8fbfa,#eef4f2)] px-6 py-16">
      <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-brand-100 bg-white/70 px-4 py-2 text-sm font-semibold text-brand-700">
            <Sparkles size={16} /> IA + Moodle + organização acadêmica
          </div>
          <h1 className="text-5xl font-bold leading-tight text-ink">Seu portal acadêmico inteligente.</h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            Organize prazos, sincronize atividades do Moodle e converse com um assistente que conhece seu contexto acadêmico.
          </p>
          <button className="button mt-8 px-6 py-3" onClick={() => navigate("/onboarding")}>
            Começar agora
          </button>
        </div>
        <div className="card overflow-hidden p-0">
          <div className="bg-brand-600 p-7 text-white">
            <GraduationCap size={42} />
            <h2 className="mt-5 text-2xl font-bold">Edu Assistant</h2>
            <p className="mt-2 text-brand-100">Uma visão clara para sua rotina de estudos.</p>
          </div>
          <div className="grid gap-3 p-7 text-sm text-slate-600">
            {["Cursos e prazos sincronizados com Moodle", "Plano diário orientado por prioridades", "Chat educacional com contexto do aluno"].map((item) => (
              <div className="flex items-center gap-3" key={item}>
                <CheckCircle2 className="text-brand-500" size={19} />
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileForm({ title = "Complete seu perfil", afterSave }: { title?: string; afterSave?: () => void }) {
  const bootstrap = useLoad(api.bootstrap);
  const [profile, setProfile] = useState<Profile>(defaultProfile);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (bootstrap.data?.profile) setProfile(bootstrap.data.profile);
  }, [bootstrap.data]);
  if (!bootstrap.data) return <div className="p-8">Carregando...</div>;
  const curriculum = bootstrap.data.curriculum[String(profile.semester)] || bootstrap.data.curriculum[profile.semester] || {};
  const disciplines = Object.entries(curriculum) as [string, { name: string }][];
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setMessage("");
    try {
      await api.saveProfile(profile);
      setMessage("Perfil salvo com sucesso.");
      afterSave?.();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-bold">{title}</h1>
      <p className="mt-2 text-slate-500">Essas informações ajudam o assistente a personalizar recomendações e respostas.</p>
      <form onSubmit={submit} className="card mt-7 grid gap-5 md:grid-cols-2">
        <label className="text-sm font-semibold md:col-span-2">
          Curso
          <input className="input mt-2" value={profile.course_name} onChange={(e) => setProfile({ ...profile, course_name: e.target.value })} />
        </label>
        <label className="text-sm font-semibold">
          Semestre
          <select className="input mt-2" value={profile.semester} onChange={(e) => setProfile({ ...profile, semester: Number(e.target.value), study_disciplines: [] })}>
            {[1, 2, 3, 4, 5, 6].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Dedicação semanal
          <input className="input mt-2" type="number" min="0" max="60" value={profile.weekly_hours ?? ""} onChange={(e) => setProfile({ ...profile, weekly_hours: Number(e.target.value) })} />
        </label>
        <label className="text-sm font-semibold md:col-span-2">
          Foco de aprendizado
          <input className="input mt-2" placeholder="Ex.: melhorar em cálculo e revisar programação" value={profile.focus || ""} onChange={(e) => setProfile({ ...profile, focus: e.target.value })} />
        </label>
        <label className="text-sm font-semibold">
          Polo
          <select className="input mt-2" value={profile.pole_name} onChange={(e) => setProfile({ ...profile, pole_name: e.target.value })}>
            {Object.keys(bootstrap.data.poles).map((pole) => (
              <option key={pole}>{pole}</option>
            ))}
          </select>
        </label>
        <div className="text-sm">
          <b>Dados do polo</b>
          <p className="mt-2 leading-6 text-slate-500">{bootstrap.data.poles[profile.pole_name]?.address}</p>
        </div>
        <div className="md:col-span-2">
          <p className="text-sm font-semibold">Disciplinas atuais</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {disciplines.map(([key, value]) => (
              <label className="flex gap-2 rounded-lg border border-slate-100 p-3 text-sm" key={key}>
                <input
                  type="checkbox"
                  checked={profile.study_disciplines.includes(key)}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      study_disciplines: e.target.checked ? [...profile.study_disciplines, key] : profile.study_disciplines.filter((item) => item !== key),
                    })
                  }
                />
                {value.name}
              </label>
            ))}
          </div>
        </div>
        {message && (
          <div className="md:col-span-2">
            <Alert>{message}</Alert>
          </div>
        )}
        <button className="button md:col-span-2">Salvar perfil</button>
      </form>
    </div>
  );
}

function Onboarding() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <ProfileForm title="Vamos personalizar seu assistente" afterSave={() => navigate("/dashboard")} />
    </div>
  );
}

const links = [
  ["/dashboard", "Visão geral", LayoutDashboard],
  ["/chat", "Chat", MessageCircle],
  ["/tasks", "Prazos", CalendarDays],
  ["/agenda", "Agenda", CalendarClock],
  ["/moodle", "Moodle", GraduationCap],
  ["/progress", "Meu progresso", TrendingUp],
  ["/recommendations", "Recomendações", Lightbulb],
  ["/profile", "Perfil", CircleUserRound],
] as const;

function Shell({ children }: { children: ReactNode }) {
  const profile = useLoad(api.profile);
  const notifications = useLoad(api.notificationSummary);
  const navigate = useNavigate();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const unreadCount = notifications.data?.unread_count || 0;
  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNotificationsOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const openNotification = async (item: AppNotification) => {
    if (!item.read) {
      await api.markNotificationRead(item.id);
      await notifications.reload();
    }
    setNotificationsOpen(false);
    if (item.action_url) navigate(item.action_url);
  };
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="bg-ink px-4 py-6 text-white">
        <div className="flex items-center gap-3 px-3">
          <div className="rounded-xl bg-brand-500 p-2">
            <GraduationCap />
          </div>
          <div>
            <b>Edu Assistant</b>
            <p className="text-xs text-slate-300">Portal Acadêmico BICT</p>
          </div>
        </div>
        <nav className="mt-9 grid gap-1">
          {links.map(([path, label, Icon]) => (
            <NavLink key={path} to={path} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${isActive ? "bg-white/15 text-white" : "text-slate-300 hover:bg-white/10"}`}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-10 rounded-xl bg-white/10 p-3 text-xs leading-5 text-slate-300">
          <b className="text-white">Perfil local</b>
          <p className="mt-1">{profile.data?.profile?.pole_name || "Complete seu perfil"}</p>
          <p>{profile.data?.profile?.semester || "-"}º semestre</p>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur lg:px-9">
          <div>
            <p className="text-sm font-semibold text-ink">Portal acadêmico</p>
            <p className="hidden text-xs text-slate-400 sm:block">Organize sua rotina de estudos em um só lugar.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative" ref={notificationsRef}>
            <button
              type="button"
              aria-label="Abrir notificações"
              aria-expanded={notificationsOpen}
              aria-haspopup="dialog"
              title="Notificações"
              onClick={() => setNotificationsOpen((open) => !open)}
              className={`relative grid h-10 w-10 place-items-center rounded-full border transition ${notificationsOpen ? "border-brand-200 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              <Bell size={19} />
              {unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-500 px-1.5 py-0.5 text-center text-[10px] font-bold leading-4 text-white">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
            {notificationsOpen && (
              <div aria-label="Painel de notificações" className="absolute right-0 top-12 z-50 w-[min(390px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <div>
                    <b className="text-sm">Notificações</b>
                    <p className="text-xs text-slate-400">{unreadCount} não lida(s)</p>
                  </div>
                  <NavLink to="/notifications" onClick={() => setNotificationsOpen(false)} className="text-xs font-semibold text-brand-700 hover:text-brand-600">
                    Ver todas
                  </NavLink>
                </div>
                <div className="max-h-96 overflow-auto p-2">
                  {notifications.error && <div className="p-3 text-sm text-red-600">{notifications.error}</div>}
                  {!notifications.data && !notifications.error && <div className="p-3 text-sm text-slate-400">Carregando...</div>}
                  {notifications.data?.notifications.length ? notifications.data.notifications.map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      onClick={() => void openNotification(item)}
                      className={`mb-1 w-full rounded-xl p-3 text-left transition hover:bg-slate-50 ${item.read ? "" : "bg-brand-50/60"}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${item.severity === "urgent" ? "bg-red-500" : item.severity === "warning" ? "bg-amber-500" : "bg-blue-500"}`} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-800">{item.title}</p>
                          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{item.message}</p>
                          <p className="mt-1 text-[11px] text-slate-400">{fmtDateTime(item.created_at)}</p>
                        </div>
                      </div>
                    </button>
                  )) : notifications.data && <div className="p-6 text-center text-sm text-slate-500">Nenhuma notificação por enquanto.</div>}
                </div>
              </div>
            )}
            </div>
            <NavLink to="/profile" className="grid h-10 w-10 place-items-center rounded-full bg-ink text-sm font-bold text-white" aria-label="Abrir perfil" title="Perfil">
              {(profile.data?.profile?.pole_name || "A").slice(0, 1).toUpperCase()}
            </NavLink>
          </div>
        </header>
        <main className="p-6 lg:p-9">{children}</main>
      </div>
    </div>
  );
}

function Dashboard() {
  const { data, error, reload } = useLoad(api.dashboard);
  const diagnostics = useLoad(api.moodleDiagnostics);
  const notificationSummary = useLoad(api.notificationSummary);
  const [notice, setNotice] = useState("");
  const [plan, setPlan] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [busy, setBusy] = useState("");
  if (!data) return <p>Carregando dashboard...</p>;
  const action = async (name: string, fn: () => Promise<any>, done: (result: any) => void) => {
    try {
      setBusy(name);
      setNotice("");
      done(await fn());
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy("");
    }
  };
  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Visão geral</h1>
          <p className="mt-2 text-slate-500">Acompanhe sua rotina acadêmica em um só lugar.</p>
        </div>
        <button
          className="button flex gap-2"
          disabled={!!busy}
          onClick={() =>
            action("sync", api.syncMoodle, (result) => {
              setNotice(`Moodle sincronizado: ${result.courses} curso(s), ${result.tasks} prazo(s) e ${result.notifications_created} notificação(ões).`);
              void reload();
              void diagnostics.reload();
              void notificationSummary.reload();
            })
          }
        >
          <RefreshCw size={17} />
          {busy === "sync" ? "Sincronizando..." : "Sincronizar Moodle"}
        </button>
      </div>
      {(notice || error) && (
        <div className="mt-5">
          <Alert error={!!error}>{error || notice}</Alert>
        </div>
      )}
      <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Semestre", `${data.profile?.semester || "-"}/6`, BookOpen],
          ["Polo", data.profile?.pole_name || "-", GraduationCap],
          ["Dedicação semanal", `${data.profile?.weekly_hours ?? "-"} h`, CalendarDays],
          ["Atividades pendentes", data.metrics.pending_tasks, CheckCircle2],
        ].map(([label, value, Icon]: any) => (
          <div className="card" key={label}>
            <Icon className="text-brand-500" size={20} />
            <p className="mt-4 text-sm text-slate-500">{label}</p>
            <b className="mt-1 block text-2xl">{value}</b>
          </div>
        ))}
      </div>
      <AgendaTodayCard blocks={data.today_blocks || []} plannedMinutes={data.planned_minutes_today || 0} />
      <NotificationSummaryCard data={notificationSummary.data} loading={!notificationSummary.data && !notificationSummary.error} error={notificationSummary.error} />
      <MoodleStatusCard diagnostics={diagnostics.data} loading={!diagnostics.data && !diagnostics.error} error={diagnostics.error} onRefresh={diagnostics.reload} />
      <section className="mt-7 grid gap-6 xl:grid-cols-[1.4fr_.8fr]">
        <div className="card">
          <h2 className="text-xl font-bold">Próximos prazos</h2>
          <div className="mt-4 grid gap-3">
            {data.upcoming_tasks.length ? (
              data.upcoming_tasks.slice(0, 5).map((task: Task) => <TaskRow task={task} key={task.id} />)
            ) : (
              <p className="text-sm text-slate-500">Nenhuma atividade pendente. Crie uma tarefa manual ou sincronize uma atividade com prazo no Moodle.</p>
            )}
          </div>
        </div>
        <div className="card">
          <h2 className="text-xl font-bold">Cursos Moodle</h2>
          <p className="mt-1 text-xs text-slate-400">{data.sync_state ? `Última sincronização: ${fmtDateTime(data.sync_state.last_synced_at)}` : "Ainda não sincronizado"}</p>
          <div className="mt-4 grid gap-2">
            {data.courses.length ? (
              data.courses.map((course: any) => (
                <div className="rounded-xl bg-brand-50 p-3" key={course.external_id}>
                  <b className="text-sm">{course.fullname}</b>
                  <p className="text-xs text-brand-700">{course.shortname}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">Nenhum curso sincronizado. Verifique o Moodle, matricule o aluno edu.student e clique em sincronizar.</p>
            )}
          </div>
        </div>
      </section>
      <section className="mt-7 grid gap-6 xl:grid-cols-2">
        <AiCard title="Plano de hoje" text={plan} loading={busy === "plan"} onClick={() => action("plan", api.todayPlan, (result) => setPlan(result.text))} />
        <AiCard title="Sugestão do dia" text={suggestion} loading={busy === "suggestion"} onClick={() => action("suggestion", api.suggestion, (result) => setSuggestion(result.text))} />
      </section>
    </>
  );
}

function AgendaTodayCard({ blocks, plannedMinutes }: { blocks: StudyBlock[]; plannedMinutes: number }) {
  return (
    <section className="card mt-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">Agenda de hoje</h2>
          <p className="mt-1 text-sm text-slate-500">{plannedMinutes ? `${plannedMinutes} minutos planejados.` : "Nenhum bloco planejado para hoje."}</p>
        </div>
        <NavLink className="button-secondary" to="/agenda">Abrir agenda</NavLink>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {blocks.length ? blocks.slice(0, 3).map((block) => (
          <div key={block.id} className="rounded-xl border border-slate-100 p-3">
            <div className="flex items-center justify-between gap-3">
              <b className="text-sm">{block.title}</b>
              <span className={`rounded-full px-2 py-0.5 text-xs ${block.status === "completed" ? "bg-emerald-50 text-emerald-700" : "bg-brand-50 text-brand-700"}`}>
                {block.status === "completed" ? "Concluído" : block.start_time}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">{block.discipline || "Estudo geral"} · {block.duration_minutes} min</p>
          </div>
        )) : <p className="text-sm text-slate-500">Configure sua disponibilidade e gere uma sugestão semanal.</p>}
      </div>
    </section>
  );
}

function MoodleStatusCard({ diagnostics, loading, error, onRefresh }: { diagnostics: MoodleDiagnostics | null; loading: boolean; error: string; onRefresh: () => Promise<void> }) {
  const [refreshing, setRefreshing] = useState(false);
  const status = diagnostics?.status || (error ? "error" : "warning");
  const color = status === "ok" ? "text-emerald-700 bg-emerald-50" : status === "warning" ? "text-amber-700 bg-amber-50" : "text-red-700 bg-red-50";
  const Icon = status === "ok" ? CheckCircle2 : AlertCircle;
  const refresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };
  return (
    <section className="card mt-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${color}`}>
            <Icon size={16} />
            {status === "ok" ? "Moodle conectado" : status === "warning" ? "Moodle requer atenção" : "Moodle com erro"}
          </div>
          <h2 className="mt-4 text-xl font-bold">Status da integração Moodle</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{loading ? "Verificando Moodle..." : error || diagnostics?.message || "Diagnóstico ainda não executado."}</p>
        </div>
        <button className="button-secondary flex gap-2" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw size={16} />
          {refreshing ? "Verificando..." : "Verificar Moodle"}
        </button>
      </div>
      {diagnostics && (
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <InfoTile label="URL" value={diagnostics.base_url} />
          <InfoTile label="Token" value={diagnostics.token_configured ? "Configurado" : "Ausente"} />
          <InfoTile label="Usuário" value={diagnostics.user?.username || diagnostics.user?.fullname || "-"} />
          <InfoTile label="Cursos do token" value={`${diagnostics.courses_count}`} />
        </div>
      )}
      {diagnostics && (
        <div className="mt-5 grid gap-2">
          {diagnostics.checks.map((check) => (
            <div key={check.label} className="flex items-start justify-between gap-4 rounded-xl border border-slate-100 p-3 text-sm">
              <div>
                <b>{check.label}</b>
                <p className="mt-1 text-slate-500">{check.detail}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${check.status === "ok" ? "bg-emerald-50 text-emerald-700" : check.status === "warning" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>
                {check.status}
              </span>
            </div>
          ))}
        </div>
      )}
      <p className="mt-4 text-xs text-slate-400">Para a demonstração: Moodle em localhost:8080, aluno edu.student matriculado e token REST configurado no backend.</p>
    </section>
  );
}

function NotificationSummaryCard({ data, loading, error }: { data: { unread_count: number; notifications: AppNotification[] } | null; loading: boolean; error: string }) {
  return (
    <section className="card mt-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">Notificações recentes</h2>
          <p className="mt-1 text-sm text-slate-500">{data ? `${data.unread_count} não lida(s)` : "Resumo de avisos importantes do Moodle e dos prazos."}</p>
        </div>
        <NavLink className="button-secondary" to="/notifications">Ver todas</NavLink>
      </div>
      <div className="mt-4 grid gap-3">
        {loading && <p className="text-sm text-slate-400">Carregando notificações...</p>}
        {error && <Alert error>{error}</Alert>}
        {data?.notifications.length ? data.notifications.slice(0, 3).map((item) => <NotificationCard key={item.id} item={item} compact />) : !loading && <p className="text-sm text-slate-500">Nenhuma notificação por enquanto.</p>}
      </div>
    </section>
  );
}

function severityClass(severity: AppNotification["severity"]) {
  if (severity === "urgent") return "border-red-100 bg-red-50 text-red-700";
  if (severity === "warning") return "border-amber-100 bg-amber-50 text-amber-700";
  return "border-blue-100 bg-blue-50 text-blue-700";
}

function NotificationCard({ item, compact = false, onRead }: { item: AppNotification; compact?: boolean; onRead?: (item: AppNotification) => void }) {
  const navigate = useNavigate();
  const openAction = () => {
    if (item.action_url) navigate(item.action_url);
  };
  return (
    <div className={`rounded-xl border p-4 ${item.read ? "border-slate-100 bg-white" : severityClass(item.severity)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <b className="text-sm text-slate-900">{item.title}</b>
            {!item.read && <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs font-semibold">Nova</span>}
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">{item.message}</p>
          {!compact && <p className="mt-2 text-xs text-slate-400">{fmtDateTime(item.created_at)}</p>}
        </div>
        {!compact && <div className="flex flex-wrap gap-2">
          {item.action_url && <button className="button-secondary" onClick={openAction}>Abrir</button>}
          {!item.read && onRead && <button className="button-secondary" onClick={() => onRead(item)}>Marcar lida</button>}
        </div>}
      </div>
    </div>
  );
}

function NotificationsPage() {
  const [filter, setFilter] = useState("all");
  const { data, error, reload } = useLoad(() => api.notifications(filter), [filter]);
  const summary = useLoad(api.notificationSummary);
  const markRead = async (item: AppNotification) => {
    await api.markNotificationRead(item.id);
    await Promise.all([reload(), summary.reload()]);
  };
  const markAll = async () => {
    await api.markAllNotificationsRead();
    await Promise.all([reload(), summary.reload()]);
  };
  const clearRead = async () => {
    await api.deleteReadNotifications();
    await Promise.all([reload(), summary.reload()]);
  };
  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Notificações</h1>
          <p className="mt-2 text-slate-500">Avisos internos sobre cursos, atividades e prazos próximos.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="button-secondary" onClick={markAll}>Marcar todas como lidas</button>
          <button className="button-secondary" onClick={clearRead}>Limpar lidas</button>
        </div>
      </div>
      <div className="mt-7 grid gap-4 md:grid-cols-3">
        <div className="card"><p className="text-sm text-slate-500">Não lidas</p><b className="mt-1 block text-2xl">{summary.data?.unread_count ?? 0}</b></div>
        <div className="card"><p className="text-sm text-slate-500">Últimas carregadas</p><b className="mt-1 block text-2xl">{data?.notifications.length ?? 0}</b></div>
        <div className="card"><p className="text-sm text-slate-500">Origem</p><b className="mt-1 block text-2xl">Moodle + local</b></div>
      </div>
      <div className="mt-7 flex flex-wrap gap-2">
        {[
          ["all", "Todas"],
          ["unread", "Não lidas"],
          ["read", "Lidas"],
        ].map(([key, label]) => <button key={key} className={filter === key ? "button" : "button-secondary"} onClick={() => setFilter(key)}>{label}</button>)}
      </div>
      <div className="mt-4 grid gap-3">
        {error && <Alert error>{error}</Alert>}
        {data?.notifications.length ? data.notifications.map((item) => <NotificationCard key={item.id} item={item} onRead={markRead} />) : <div className="card text-sm text-slate-500">Nenhuma notificação neste filtro.</div>}
      </div>
    </>
  );
}

const weekdayNames = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

function AgendaPage() {
  const navigate = useNavigate();
  const [weekStart, setWeekStart] = useState(startOfWeek);
  const [view, setView] = useState<"today" | "week">("today");
  const [availabilityDraft, setAvailabilityDraft] = useState<AvailabilitySlot[]>([]);
  const [suggestions, setSuggestions] = useState<AgendaSuggestion[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [editingBlock, setEditingBlock] = useState<number | null>(null);
  const [reschedule, setReschedule] = useState({ study_date: isoDate(new Date()), start_time: "18:00", duration_minutes: 60 as 30 | 60 | 90 });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const rangeStart = isoDate(weekStart);
  const rangeEnd = isoDate(addDays(weekStart, 6));
  const today = isoDate(new Date());
  const availability = useLoad(api.availability);
  const agenda = useLoad(() => api.agenda(rangeStart, rangeEnd), [rangeStart, rangeEnd]);

  useEffect(() => {
    if (availability.data) setAvailabilityDraft(availability.data.availability);
  }, [availability.data]);

  const slotForDay = (weekday: number) => availabilityDraft.find((slot) => slot.weekday === weekday);
  const toggleDay = (weekday: number) => {
    const existing = slotForDay(weekday);
    setAvailabilityDraft(existing
      ? availabilityDraft.filter((slot) => slot.weekday !== weekday)
      : [...availabilityDraft, { weekday, start_time: "18:00", end_time: "20:00" }]);
  };
  const updateSlot = (weekday: number, field: "start_time" | "end_time", value: string) => {
    setAvailabilityDraft(availabilityDraft.map((slot) => slot.weekday === weekday ? { ...slot, [field]: value } : slot));
  };
  const saveAvailability = async () => {
    setBusy("availability");
    setNotice("");
    try {
      await api.saveAvailability(availabilityDraft);
      setNotice("Disponibilidade semanal salva.");
      await availability.reload();
    } catch (error) {
      setNotice((error as Error).message);
    } finally {
      setBusy("");
    }
  };
  const generate = async () => {
    setBusy("suggestions");
    setNotice("");
    try {
      const result = await api.agendaSuggestions(rangeStart);
      setSuggestions(result.suggestions);
      setSelected(new Set(result.suggestions.map((_, index) => index)));
      if (!result.suggestions.length) setNotice("Nenhuma nova sugestão foi gerada. Verifique tarefas pendentes e horários disponíveis.");
    } catch (error) {
      setNotice((error as Error).message);
    } finally {
      setBusy("");
    }
  };
  const confirmSuggestions = async () => {
    const blocks = suggestions.filter((_, index) => selected.has(index));
    if (!blocks.length) return;
    setBusy("confirm");
    setNotice("");
    try {
      await api.createStudyBlocks(blocks);
      setSuggestions([]);
      setSelected(new Set());
      setNotice(`${blocks.length} bloco(s) adicionado(s) à agenda.`);
      await agenda.reload();
    } catch (error) {
      setNotice((error as Error).message);
    } finally {
      setBusy("");
    }
  };
  const completeBlock = async (block: StudyBlock) => {
    await api.completeStudyBlock(block.id);
    await agenda.reload();
  };
  const beginReschedule = (block: StudyBlock) => {
    setEditingBlock(block.id);
    setReschedule({ study_date: block.study_date, start_time: block.start_time, duration_minutes: block.duration_minutes });
  };
  const saveReschedule = async (block: StudyBlock) => {
    try {
      await api.rescheduleStudyBlock(block.id, reschedule);
      setEditingBlock(null);
      await agenda.reload();
    } catch (error) {
      setNotice((error as Error).message);
    }
  };
  const displayedDays = view === "today"
    ? [new Date(`${today}T12:00:00`)]
    : Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Agenda inteligente</h1>
          <p className="mt-2 text-slate-500">Transforme tarefas pendentes em blocos de estudo que cabem na sua semana.</p>
        </div>
        <button className="button flex items-center gap-2" onClick={generate} disabled={!!busy}>
          <Sparkles size={16}/>{busy === "suggestions" ? "Gerando..." : "Gerar sugestões"}
        </button>
      </div>
      {notice && <div className="mt-5"><Alert error={notice.toLowerCase().includes("inválid") || notice.toLowerCase().includes("sobrepõe")}>{notice}</Alert></div>}

      <section className="card mt-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Disponibilidade semanal</h2>
            <p className="mt-1 text-sm text-slate-500">Escolha os períodos recorrentes em que você normalmente consegue estudar.</p>
          </div>
          <button className="button-secondary" onClick={saveAvailability} disabled={busy === "availability"}>
            {busy === "availability" ? "Salvando..." : "Salvar disponibilidade"}
          </button>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {weekdayNames.map((name, weekday) => {
            const slot = slotForDay(weekday);
            return <div className={`rounded-xl border p-3 ${slot ? "border-brand-100 bg-brand-50/40" : "border-slate-100"}`} key={name}>
              <label className="flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" checked={!!slot} onChange={() => toggleDay(weekday)}/>{name}
              </label>
              {slot && <div className="mt-3 flex items-center gap-2">
                <input aria-label={`Início ${name}`} className="input px-2 py-2" type="time" value={slot.start_time} onChange={(event) => updateSlot(weekday, "start_time", event.target.value)}/>
                <span className="text-xs text-slate-400">até</span>
                <input aria-label={`Fim ${name}`} className="input px-2 py-2" type="time" value={slot.end_time} onChange={(event) => updateSlot(weekday, "end_time", event.target.value)}/>
              </div>}
            </div>;
          })}
        </div>
      </section>

      {suggestions.length > 0 && <section className="card mt-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Sugestões para confirmar</h2>
            <p className="mt-1 text-sm text-slate-500">Revise horários e duração. Nada será salvo sem sua confirmação.</p>
          </div>
          <button className="button" onClick={confirmSuggestions} disabled={!selected.size || busy === "confirm"}>
            {busy === "confirm" ? "Confirmando..." : `Confirmar ${selected.size} bloco(s)`}
          </button>
        </div>
        <div className="mt-5 grid gap-3">
          {suggestions.map((suggestion, index) => <div className="rounded-xl border border-slate-100 p-4" key={`${suggestion.task_id}-${index}`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <label className="flex min-w-0 gap-3">
                <input type="checkbox" checked={selected.has(index)} onChange={() => {
                  const next = new Set(selected);
                  next.has(index) ? next.delete(index) : next.add(index);
                  setSelected(next);
                }}/>
                <div>
                  <b>{suggestion.title}</b>
                  <p className="mt-1 text-sm text-slate-500">{suggestion.discipline || "Estudo geral"} · {suggestion.reason}</p>
                </div>
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <input aria-label={`Data ${suggestion.title}`} className="input w-auto" type="date" value={suggestion.study_date} onChange={(event) => setSuggestions(suggestions.map((item, itemIndex) => itemIndex === index ? { ...item, study_date: event.target.value } : item))}/>
                <input aria-label={`Horário ${suggestion.title}`} className="input w-auto" type="time" value={suggestion.start_time} onChange={(event) => setSuggestions(suggestions.map((item, itemIndex) => itemIndex === index ? { ...item, start_time: event.target.value } : item))}/>
                <select aria-label={`Duração ${suggestion.title}`} className="input w-auto" value={suggestion.duration_minutes} onChange={(event) => setSuggestions(suggestions.map((item, itemIndex) => itemIndex === index ? { ...item, duration_minutes: Number(event.target.value) as 30 | 60 | 90 } : item))}>
                  <option value={30}>30 min</option><option value={60}>60 min</option><option value={90}>90 min</option>
                </select>
              </div>
            </div>
          </div>)}
        </div>
      </section>}

      <section className="mt-7">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-2">
            <button className={view === "today" ? "button" : "button-secondary"} onClick={() => setView("today")}>Hoje</button>
            <button className={view === "week" ? "button" : "button-secondary"} onClick={() => setView("week")}>Semana</button>
          </div>
          {view === "week" && <div className="flex items-center gap-2">
            <button aria-label="Semana anterior" className="button-secondary" onClick={() => setWeekStart(addDays(weekStart, -7))}>‹</button>
            <span className="text-sm font-semibold">{fmt(rangeStart)} - {fmt(rangeEnd)}</span>
            <button aria-label="Próxima semana" className="button-secondary" onClick={() => setWeekStart(addDays(weekStart, 7))}>›</button>
          </div>}
        </div>
        <div className={`mt-4 grid gap-4 ${view === "week" ? "xl:grid-cols-7" : ""}`}>
          {displayedDays.map((day) => {
            const dayKey = isoDate(day);
            const blocks = (agenda.data?.blocks || []).filter((block) => block.study_date === dayKey);
            return <div className="card p-4" key={dayKey}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{weekdayNames[(day.getDay() + 6) % 7]}</p>
              <b className="mt-1 block">{fmt(dayKey)}</b>
              <div className="mt-4 grid gap-3">
                {blocks.length ? blocks.map((block) => <div className={`rounded-xl border p-3 ${block.status === "completed" ? "border-emerald-100 bg-emerald-50/50" : "border-brand-100 bg-brand-50/40"}`} key={block.id}>
                  <div className="flex items-center justify-between gap-2">
                    <b className="text-sm">{block.title}</b>
                    <span className="text-xs font-semibold text-brand-700">{block.start_time}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{block.discipline || "Estudo geral"} · {block.duration_minutes} min</p>
                  {editingBlock === block.id ? <div className="mt-3 grid gap-2">
                    <input aria-label={`Nova data ${block.title}`} className="input" type="date" value={reschedule.study_date} onChange={(event) => setReschedule({ ...reschedule, study_date: event.target.value })}/>
                    <input aria-label={`Novo horário ${block.title}`} className="input" type="time" value={reschedule.start_time} onChange={(event) => setReschedule({ ...reschedule, start_time: event.target.value })}/>
                    <select aria-label={`Nova duração ${block.title}`} className="input" value={reschedule.duration_minutes} onChange={(event) => setReschedule({ ...reschedule, duration_minutes: Number(event.target.value) as 30 | 60 | 90 })}>
                      <option value={30}>30 min</option><option value={60}>60 min</option><option value={90}>90 min</option>
                    </select>
                    <div className="flex gap-2"><button className="button" onClick={() => saveReschedule(block)}>Salvar</button><button className="button-secondary" onClick={() => setEditingBlock(null)}>Cancelar</button></div>
                  </div> : <div className="mt-3 flex flex-wrap gap-2">
                    {block.status === "planned" && <button className="button-secondary" onClick={() => completeBlock(block)}>Concluir</button>}
                    <button aria-label={`Reagendar ${block.title}`} className="button-secondary" onClick={() => beginReschedule(block)}><RotateCcw size={14}/></button>
                    <button className="button-secondary" onClick={() => navigate(`/chat?prompt=${encodeURIComponent(`Me ajude com o bloco de estudo "${block.title}" de ${block.duration_minutes} minutos.`)}`)}>Perguntar</button>
                    {block.task_id && <button className="button-secondary" onClick={() => navigate("/tasks")}>Ver tarefa</button>}
                  </div>}
                </div>) : <p className="text-sm text-slate-400">Sem blocos.</p>}
              </div>
            </div>;
          })}
        </div>
      </section>
    </>
  );
}

function MoodlePage() {
  const diagnostics = useLoad(api.moodleDiagnostics);
  const dashboard = useLoad(api.dashboard);
  const tasks = useLoad(api.tasks);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const moodleTasks = (tasks.data?.tasks || []).filter((task) => task.source === "moodle");
  const sync = async () => {
    setBusy(true);
    setNotice("");
    try {
      const result = await api.syncMoodle();
      setNotice(`Sincronização concluída: ${result.courses} curso(s), ${result.tasks} prazo(s) e ${result.notifications_created} notificação(ões).`);
      await Promise.all([diagnostics.reload(), dashboard.reload(), tasks.reload()]);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Moodle</h1>
          <p className="mt-2 text-slate-500">Central da integração Moodle: diagnóstico, cursos importados e prazos sincronizados.</p>
        </div>
        <button className="button flex gap-2" disabled={busy} onClick={sync}>
          <RefreshCw size={17} />
          {busy ? "Sincronizando..." : "Sincronizar Moodle"}
        </button>
      </div>
      {notice && (
        <div className="mt-5">
          <Alert error={notice.toLowerCase().includes("erro") || notice.toLowerCase().includes("moodle indisponível")}>{notice}</Alert>
        </div>
      )}
      <MoodleStatusCard diagnostics={diagnostics.data} loading={!diagnostics.data && !diagnostics.error} error={diagnostics.error} onRefresh={diagnostics.reload} />
      <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <InfoTile label="Usuário token" value={diagnostics.data?.user?.username || "-"} />
        <InfoTile label="Cursos matriculados" value={`${diagnostics.data?.courses_count ?? dashboard.data?.courses.length ?? 0}`} />
        <InfoTile label="Cursos importados" value={`${dashboard.data?.courses.length ?? 0}`} />
        <InfoTile label="Última sincronização" value={fmtDateTime(dashboard.data?.sync_state?.last_synced_at)} />
      </div>
      <section className="mt-7 grid gap-6 xl:grid-cols-2">
        <div className="card">
          <h2 className="text-xl font-bold">Cursos importados</h2>
          <p className="mt-1 text-sm text-slate-500">Esses cursos aparecem quando o aluno do token está matriculado no Moodle.</p>
          <div className="mt-4 grid gap-3">
            {dashboard.data?.courses.length ? (
              dashboard.data.courses.map((course: { external_id: string; fullname: string; shortname?: string }) => (
                <div className="rounded-xl border border-slate-100 p-4" key={course.external_id}>
                  <b>{course.fullname}</b>
                  <p className="mt-1 text-sm text-slate-500">{course.shortname}</p>
                </div>
              ))
            ) : (
              <Alert>
                Nenhum curso importado ainda. No Moodle, matricule o usuário edu.student no curso desejado e execute a sincronização nesta tela.
              </Alert>
            )}
          </div>
        </div>
        <div className="card">
          <h2 className="text-xl font-bold">Prazos vindos do Moodle</h2>
          <p className="mt-1 text-sm text-slate-500">Somente eventos acadêmicos com prazo aparecem aqui.</p>
          <div className="mt-4 grid gap-3">
            {moodleTasks.length ? (
              moodleTasks.map((task) => <TaskRow task={task} key={task.id} />)
            ) : (
              <Alert>
                Nenhum prazo Moodle foi importado. Crie uma atividade com data no Moodle, confirme a matrícula do edu.student e sincronize novamente.
              </Alert>
            )}
          </div>
        </div>
      </section>
    </>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-700">{value}</p>
    </div>
  );
}

function AiCard({ title, text, loading, onClick }: { title: string; text: string; loading: boolean; onClick: () => void }) {
  return (
    <div className="card">
      <div className="flex justify-between gap-4">
        <h2 className="text-xl font-bold">{title}</h2>
        <button className="button-secondary flex gap-2" disabled={loading} onClick={onClick}>
          <Sparkles size={16} />
          {loading ? "Gerando..." : "Gerar com IA"}
        </button>
      </div>
      <p className="mt-4 whitespace-pre-line text-sm leading-6 text-slate-600">{text || "Gere quando quiser uma orientação personalizada."}</p>
    </div>
  );
}

function TaskRow({ task, action }: { task: Task; action?: ReactNode }) {
  const severityClass = task.deadline.code === "OVERDUE"
    ? "border-red-100 bg-red-50/40"
    : task.deadline.severity >= 3
      ? "border-amber-100 bg-amber-50/40"
      : "border-slate-100 bg-white";
  return (
    <div className={`flex items-center justify-between gap-3 rounded-xl border p-3 ${severityClass}`}>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <b className="text-sm">{task.title}</b>
          <span className={`rounded-full px-2 py-0.5 text-xs ${task.source === "moodle" ? "bg-blue-50 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
            {task.source === "moodle" ? "Moodle" : "Manual"}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-xs ${task.deadline.code === "OVERDUE" ? "bg-red-100 text-red-700" : task.deadline.severity >= 3 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"}`}>
            {task.deadline.label}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {task.discipline || "Sem disciplina"} · {fmt(task.due_date)}
        </p>
      </div>
      {action}
    </div>
  );
}

function Tasks() {
  const { data, reload } = useLoad(api.tasks);
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", discipline: "", due_date: new Date().toISOString().slice(0, 10), notes: "" });
  const [filter, setFilter] = useState("PENDING");
  const [sourceFilter, setSourceFilter] = useState("all");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await api.createTask(form);
    setForm({ ...form, title: "", notes: "" });
    await reload();
  };
  const tasks = (data?.tasks || [])
    .filter((task: Task) => task.status === filter)
    .filter((task: Task) => sourceFilter === "all" || task.source === sourceFilter);
  const askAboutTask = (task: Task) => {
    const prompt = `Me ajude a estudar para a atividade "${task.title}"${task.discipline ? ` de ${task.discipline}` : ""}, que vence em ${fmt(task.due_date)}.`;
    navigate(`/chat?prompt=${encodeURIComponent(prompt)}`);
  };
  return (
    <>
      <h1 className="text-3xl font-bold">Prazos e atividades</h1>
      <p className="mt-2 text-slate-500">Acompanhe tarefas do Moodle e compromissos criados manualmente.</p>
      <form className="card mt-7 grid gap-3 md:grid-cols-[1fr_1fr_180px_auto]" onSubmit={submit}>
        <input required className="input" placeholder="Título da atividade" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <input className="input" placeholder="Disciplina (opcional)" value={form.discipline} onChange={(e) => setForm({ ...form, discipline: e.target.value })} />
        <input className="input" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
        <button className="button flex items-center gap-2">
          <Plus size={16} />
          Adicionar
        </button>
      </form>
      <div className="mt-7 flex flex-wrap gap-2">
        {[
          ["PENDING", "Pendentes"],
          ["DONE", "Concluídas"],
        ].map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)} className={filter === key ? "button" : "button-secondary"}>
            {label}
          </button>
        ))}
        {[
          ["all", "Todas as origens"],
          ["moodle", "Moodle"],
          ["manual", "Manuais"],
        ].map(([key, label]) => (
          <button key={key} onClick={() => setSourceFilter(key)} className={sourceFilter === key ? "button" : "button-secondary"}>
            {label}
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-5">
        {tasks.length ? (
          filter === "PENDING" ? (
            <TaskGroups
              tasks={tasks}
              onAsk={askAboutTask}
              onStatus={async (task) => {
                await api.setTaskStatus(task.id, "DONE");
                await reload();
              }}
            />
          ) : (
            <div className="card grid gap-3">
              {tasks.map((task: Task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  action={
                    <button className="button-secondary" onClick={async () => {
                      await api.setTaskStatus(task.id, "PENDING");
                      await reload();
                    }}>
                      Reabrir
                    </button>
                  }
                />
              ))}
            </div>
          )
        ) : (
          <div className="card text-sm text-slate-500">Nenhuma atividade nesta lista.</div>
        )}
      </div>
    </>
  );
}

function TaskGroups({ tasks, onAsk, onStatus }: { tasks: Task[]; onAsk: (task: Task) => void; onStatus: (task: Task) => Promise<void> }) {
  const groups = [
    { title: "Atrasadas", hint: "Resolva primeiro para reduzir risco acadêmico.", items: tasks.filter((task) => task.deadline.code === "OVERDUE") },
    { title: "Hoje", hint: "Essas atividades precisam de ação imediata.", items: tasks.filter((task) => task.deadline.days_left === 0 && task.deadline.code !== "OVERDUE") },
    { title: "Esta semana", hint: "Planeje blocos curtos para avançar antes do prazo.", items: tasks.filter((task) => task.deadline.days_left > 0 && task.deadline.days_left <= 7) },
    { title: "Depois", hint: "Mantenha no radar, mas priorize o que vence antes.", items: tasks.filter((task) => task.deadline.days_left > 7) },
  ];
  return (
    <>
      {groups.map((group) => (
        <section className="card" key={group.title}>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold">{group.title}</h2>
              <p className="mt-1 text-sm text-slate-500">{group.hint}</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{group.items.length}</span>
          </div>
          <div className="mt-4 grid gap-3">
            {group.items.length ? group.items.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                action={
                  <div className="flex flex-wrap justify-end gap-2">
                    <button className="button-secondary" onClick={() => onAsk(task)}>Perguntar ao assistente</button>
                    <button className="button-secondary" onClick={() => void onStatus(task)}>Concluir</button>
                  </div>
                }
              />
            )) : <p className="text-sm text-slate-400">Nada por aqui.</p>}
          </div>
        </section>
      ))}
    </>
  );
}

function Chat() {
  const conversations = useLoad(api.conversations);
  const context = useLoad(api.chatContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<number>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const quickPrompts = [
    "Resuma meus prazos mais importantes.",
    "Crie um plano de estudo para hoje.",
    "Quais temas eu deveria priorizar?",
    "Explique a atividade Moodle mais próxima.",
  ];
  useEffect(() => {
    if (!selected && conversations.data?.conversations[0]) setSelected(conversations.data.conversations[0].id);
  }, [conversations.data, selected]);
  useEffect(() => {
    const prompt = searchParams.get("prompt");
    if (prompt) {
      setText(prompt);
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);
  useEffect(() => {
    if (selected) void api.messages(selected).then((result) => setMessages(result.messages));
  }, [selected]);
  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);
  const create = async () => {
    const result = await api.createConversation();
    setSelected(result.id);
    await conversations.reload();
  };
  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !text.trim()) return;
    const value = text;
    setText("");
    setMessages((items) => [...items, { role: "user", content: value }]);
    setBusy(true);
    try {
      await api.sendMessage(selected, value);
      setMessages((await api.messages(selected)).messages);
      await conversations.reload();
      await context.reload();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="grid h-[calc(100vh-72px)] gap-5 xl:grid-cols-[260px_1fr_320px]">
      <div className="card overflow-auto">
        <button className="button flex w-full gap-2" onClick={create}>
          <Plus size={16} />
          Novo chat
        </button>
        <div className="mt-4 grid gap-2">
          {conversations.data?.conversations.map((conversation: Conversation) => (
            <button key={conversation.id} onClick={() => setSelected(conversation.id)} className={`rounded-xl p-3 text-left text-sm ${selected === conversation.id ? "bg-brand-50 text-brand-700" : "hover:bg-slate-50"}`}>
              {conversation.title}
            </button>
          ))}
        </div>
      </div>
      <div className="card flex min-h-0 flex-col p-0">
        <div className="border-b border-slate-100 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold">Chat educacional</h1>
              <p className="text-sm text-slate-500">Pergunte sobre seus estudos, cursos e prazos.</p>
            </div>
            {(context.data?.courses.length || context.data?.upcoming_tasks.length) ? (
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">Usando contexto Moodle</span>
            ) : (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">Contexto local</span>
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {quickPrompts.map((prompt) => (
              <button key={prompt} type="button" className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-brand-50 hover:text-brand-700" onClick={() => setText(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 space-y-4 overflow-auto p-5">
          {messages.map((message, index) => (
            <div key={index} className={`max-w-[80%] rounded-2xl p-4 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-brand-600 text-white" : "bg-slate-100 text-slate-700"}`}>
              {message.topic && message.role === "user" && (
                <div className="mb-2 text-xs font-semibold opacity-80">Tópico detectado: {message.topic}</div>
              )}
              <div>{message.content}</div>
            </div>
          ))}
          {busy && <div className="text-sm text-slate-400">Preparando resposta...</div>}
          <div ref={bottom} />
        </div>
        <form onSubmit={send} className="flex gap-3 border-t border-slate-100 p-4">
          <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Digite sua dúvida..." />
          <button className="button" disabled={busy}>
            <Send size={17} />
          </button>
        </form>
      </div>
      <ChatContextPanel context={context.data} loading={!context.data && !context.error} error={context.error} />
    </div>
  );
}

function ChatContextPanel({ context, loading, error }: { context: ChatContext | null; loading: boolean; error: string }) {
  return (
    <aside className="card min-h-0 overflow-auto">
      <h2 className="text-lg font-bold">Contexto usado pelo assistente</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">O backend envia esses dados ao chat sem expor tokens do Moodle ou da OpenAI.</p>
      {loading && <p className="mt-5 text-sm text-slate-400">Carregando contexto...</p>}
      {error && <Alert error>{error}</Alert>}
      {context && (
        <div className="mt-5 grid gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Perfil</p>
            <div className="mt-2 rounded-xl bg-slate-50 p-3 text-sm leading-6 text-slate-600">
              <b>{context.profile?.course_name || "Perfil não preenchido"}</b>
              <p>{context.profile?.semester || "-"}º semestre · {context.profile?.pole_name || "Sem polo"}</p>
              <p>{context.profile?.weekly_hours ?? "-"} h semanais</p>
            </div>
          </div>
          <ContextList title="Cursos Moodle" empty="Nenhum curso sincronizado.">
            {context.courses.slice(0, 4).map((course) => (
              <div key={course.external_id} className="rounded-xl border border-slate-100 p-3 text-sm">
                <b>{course.fullname}</b>
                <p className="text-xs text-slate-500">{course.shortname}</p>
              </div>
            ))}
          </ContextList>
          <ContextList title="Próximos prazos" empty="Nenhum prazo pendente.">
            {context.upcoming_tasks.slice(0, 4).map((task) => (
              <div key={task.id} className="rounded-xl border border-slate-100 p-3 text-sm">
                <b>{task.title}</b>
                <p className="text-xs text-slate-500">{fmt(task.due_date)} · {task.source === "moodle" ? "Moodle" : "Manual"}</p>
              </div>
            ))}
          </ContextList>
          <ContextList title="Tópicos recentes" empty="Faça perguntas para gerar tópicos.">
            {context.topics.slice(0, 4).map((topic) => (
              <div key={topic.topic} className="flex justify-between rounded-xl bg-slate-50 p-3 text-sm">
                <span>{topic.topic}</span>
                <b>{topic.count}</b>
              </div>
            ))}
          </ContextList>
          <p className="rounded-xl bg-brand-50 p-3 text-xs leading-5 text-brand-700">Última sincronização Moodle: {fmtDateTime(context.sync_state?.last_synced_at)}</p>
        </div>
      )}
    </aside>
  );
}

function ContextList({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
      <div className="mt-2 grid gap-2">{hasChildren ? children : <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500">{empty}</p>}</div>
    </div>
  );
}

function Insights({ recommendations = false }: { recommendations?: boolean }) {
  const { data, error } = useLoad(api.insights);
  if (!data && !error) return <p>Carregando análise...</p>;
  if (error) return <Alert error>{error}</Alert>;
  return recommendations ? <RecommendationsView data={data!} /> : <ProgressView data={data!} />;
}

function ProgressView({ data }: { data: InsightsData }) {
  const topTopic = data.topics[0];
  const pressure = data.progress.overdue > 0 ? "Há prazos atrasados" : data.progress.due_soon > 0 ? "Há prazos próximos" : "Sem pressão imediata";
  const cards = [
    ["Perguntas feitas", data.progress.total_questions, MessageCircle],
    ["Tópicos ativos", data.progress.active_topics, TrendingUp],
    ["Pendências", data.progress.pending_tasks, CalendarDays],
    ["Cursos Moodle", data.progress.moodle_courses, GraduationCap],
  ] as const;
  return (
    <>
      <h1 className="text-3xl font-bold">Meu progresso</h1>
      <p className="mt-2 text-slate-500">Veja como suas perguntas, prazos e cursos estão formando seu mapa de estudo.</p>
      <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value, Icon]) => (
          <div className="card" key={label}>
            <Icon className="text-brand-500" size={20} />
            <p className="mt-4 text-sm text-slate-500">{label}</p>
            <b className="mt-1 block text-2xl">{value}</b>
          </div>
        ))}
      </div>
      <section className="mt-7 grid gap-6 xl:grid-cols-3">
        <div className="card xl:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Leitura rápida</p>
          <h2 className="mt-3 text-2xl font-bold">{topTopic ? `Seu foco recente é ${topTopic.topic}` : "Ainda falta histórico de estudo"}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {topTopic
              ? `${topTopic.count} pergunta(s) foram classificadas nesse tema. Use esse dado para orientar revisão, exercícios e dúvidas no chat.`
              : "Faça perguntas no chat e sincronize o Moodle para o sistema enxergar padrões reais da sua rotina."}
          </p>
        </div>
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Pressão acadêmica</p>
          <h2 className="mt-3 text-2xl font-bold">{pressure}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {data.progress.overdue > 0
              ? "Priorize regularizar o que venceu antes de avançar para temas novos."
              : data.progress.due_soon > 0
                ? "Reserve blocos curtos para os próximos sete dias e use o chat para quebrar tarefas grandes."
                : "Bom momento para revisar o tema mais perguntado e adiantar entregas futuras."}
          </p>
        </div>
      </section>
      <section className="mt-7 grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <div className="card">
          <h2 className="text-xl font-bold">Foco das perguntas</h2>
          <p className="mt-1 text-sm text-slate-500">Os temas mais frequentes mostram onde você está buscando mais apoio.</p>
          <TopicBars topics={data.topics} />
        </div>
        <div className="card">
          <h2 className="text-xl font-bold">Situação acadêmica</h2>
          <div className="mt-4 grid gap-3 text-sm">
            <StatusLine label="Atividades concluídas" value={data.progress.completed_tasks} />
            <StatusLine label="Prazos nesta semana" value={data.progress.due_soon} />
            <StatusLine label="Atrasadas" value={data.progress.overdue} />
          </div>
          <p className="mt-5 rounded-xl bg-brand-50 p-4 text-sm leading-6 text-brand-700">{data.recommendations[0]?.description || "Faça perguntas no chat e sincronize o Moodle para enriquecer seu progresso."}</p>
        </div>
      </section>
    </>
  );
}

function RecommendationsView({ data }: { data: InsightsData }) {
  const priorityClass = (priority: string) => priority === "Alta" ? "bg-red-50 text-red-700" : priority === "Média" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600";
  return (
    <>
      <h1 className="text-3xl font-bold">Recomendações</h1>
      <p className="mt-2 text-slate-500">Ações práticas geradas a partir de perguntas no chat, prazos e dados importados do Moodle.</p>
      <div className="mt-7 grid gap-4 md:grid-cols-3">
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Prioridade agora</p>
          <b className="mt-3 block text-xl">{data.recommendations[0]?.title || "Gerar histórico"}</b>
          <p className="mt-2 text-sm text-slate-500">{data.recommendations[0]?.description || "Faça perguntas no chat para criar recomendações melhores."}</p>
        </div>
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Tema mais forte</p>
          <b className="mt-3 block text-xl">{data.topics[0]?.topic || "Sem tema ainda"}</b>
          <p className="mt-2 text-sm text-slate-500">{data.topics[0] ? `${data.topics[0].count} pergunta(s) recentes.` : "Use o chat para mapear dúvidas."}</p>
        </div>
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Risco de prazo</p>
          <b className="mt-3 block text-xl">{data.progress.overdue ? `${data.progress.overdue} atrasada(s)` : `${data.progress.due_soon} nesta semana`}</b>
          <p className="mt-2 text-sm text-slate-500">Esse número vem dos prazos manuais e dos prazos importados do Moodle.</p>
        </div>
      </div>
      <div className="mt-7 grid gap-4 xl:grid-cols-2">
        {data.recommendations.length ? (
          data.recommendations.map((item) => (
            <div className="card" key={item.title}>
              <div className="flex items-start justify-between gap-4">
                <h2 className="text-xl font-bold">{item.title}</h2>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${priorityClass(item.priority)}`}>
                  {item.priority}
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">{item.description}</p>
            </div>
          ))
        ) : (
          <div className="card text-sm text-slate-500">Faça perguntas no chat para gerar recomendações personalizadas.</div>
        )}
      </div>
      <div className="card mt-7">
        <h2 className="text-xl font-bold">Plano rápido sugerido</h2>
        <p className="mt-4 whitespace-pre-line text-sm leading-6 text-slate-600">{data.recommendation}</p>
      </div>
    </>
  );
}

function TopicBars({ topics }: { topics: InsightsData["topics"] }) {
  if (!topics.length) return <p className="mt-4 text-sm text-slate-500">Ainda não há perguntas suficientes para montar um ranking. Use o chat para começar.</p>;
  return (
    <div className="mt-5 grid gap-4">
      {topics.map((topic) => (
        <div key={topic.topic}>
          <div className="flex justify-between text-sm">
            <b>{topic.topic}</b>
            <span>{topic.count} pergunta(s)</span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-slate-100">
            <div className="h-2 rounded-full bg-brand-500" style={{ width: `${Math.max(topic.percent, 8)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function AppShell() {
  return (
    <Shell>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/agenda" element={<AgendaPage />} />
        <Route path="/moodle" element={<MoodlePage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/progress" element={<Insights />} />
        <Route path="/recommendations" element={<Insights recommendations />} />
        <Route path="/profile" element={<ProfileForm title="Editar perfil" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Shell>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/*" element={<AppShell />} />
    </Routes>
  );
}
