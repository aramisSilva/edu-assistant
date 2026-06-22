import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const profile = {
  id: 1,
  course_name: "BICT",
  semester: 4,
  pole_name: "Fortaleza",
  weekly_hours: 10,
  focus: "Organização",
  study_disciplines: ["Cálculo IV"],
};

const moodleCourse = { external_id: "10", shortname: "CALC4", fullname: "Cálculo IV" };

const moodleTask = {
  id: 12,
  title: "Lista de integrais",
  discipline: "Cálculo IV",
  due_date: "2030-01-01",
  status: "PENDING",
  notes: "",
  source: "moodle",
  deadline: { code: "UPCOMING", label: "vence em breve", days_left: 3, severity: 3 },
};

const dashboard = {
  profile,
  metrics: { pending_tasks: 1, due_within_7_days: 1 },
  courses: [moodleCourse],
  sync_state: { moodle_user_id: 7, moodle_username: "edu.student", last_synced_at: "2026-06-08T10:00:00" },
  upcoming_tasks: [moodleTask],
  topics: [],
};

const diagnostics = {
  status: "ok",
  base_url: "http://localhost:8080",
  token_configured: true,
  moodle_available: true,
  user: { id: 7, username: "edu.student", fullname: "Edu Student" },
  courses_count: 2,
  last_sync: null,
  message: "Integração Moodle pronta para sincronizar.",
  checks: [
    { label: "URL Moodle", status: "ok", detail: "http://localhost:8080" },
    { label: "Token REST", status: "ok", detail: "Token configurado." },
  ],
};

const chatContext = {
  profile,
  courses: [moodleCourse],
  upcoming_tasks: [moodleTask],
  topics: [{ topic: "Derivadas", count: 2 }],
  sync_state: dashboard.sync_state,
};

const insights = {
  progress: {
    total_questions: 3,
    active_topics: 2,
    pending_tasks: 1,
    completed_tasks: 2,
    moodle_courses: 1,
    due_soon: 1,
    overdue: 0,
  },
  topics: [
    { topic: "Limites", count: 2, percent: 67 },
    { topic: "Derivadas", count: 1, percent: 33 },
  ],
  recommendations: [
    { title: "Proteja os próximos prazos", priority: "Alta", description: "1 prazo exige atenção nesta semana." },
    { title: "Reforce Limites", priority: "Média", description: "Esse foi seu tema mais perguntado." },
  ],
  recommendation: "Plano rápido sugerido",
};

const notification = {
  id: 1,
  type: "deadline",
  severity: "warning",
  title: "Prazo vence em 3 dias",
  message: "A atividade Lista de integrais vence em 3 dias.",
  read: false,
  created_at: "2026-06-08T10:00:00",
  related_kind: "task",
  related_id: "12",
  action_url: "/tasks",
};

const notificationSummary = {
  unread_count: 1,
  notifications: [notification],
};

const localIsoDate = (value = new Date()) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const agendaBlock = {
  id: 30,
  task_id: 12,
  title: "Lista de integrais",
  discipline: "Cálculo IV",
  study_date: localIsoDate(),
  start_time: "18:00",
  duration_minutes: 60,
  origin: "suggested",
  status: "planned",
  task_due_date: "2030-01-01",
  task_source: "moodle",
};

const agendaSuggestion = {
  task_id: 12,
  title: "Lista de integrais",
  discipline: "Cálculo IV",
  study_date: localIsoDate(),
  start_time: "19:00",
  duration_minutes: 60,
  origin: "suggested",
  reason: "Prazo em 3 dias; origem Moodle.",
  task_due_date: "2030-01-01",
  task_source: "moodle",
};

function json(data: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Edu Assistant web", () => {
  it("renders the portal welcome screen", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("Seu portal acadêmico inteligente.")).toBeTruthy();
    expect(screen.getByText("Começar agora")).toBeTruthy();
  });

  it("synchronizes Moodle from the dashboard", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/dashboard")) return json(dashboard);
      if (path.endsWith("/api/moodle/diagnostics")) return json(diagnostics);
      if (path.endsWith("/api/moodle/sync")) return json({ courses: 2, tasks: 1, notifications_created: 3 });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Status da integração Moodle")).toBeTruthy();
    expect(await screen.findByText("Moodle conectado")).toBeTruthy();
    const bell = await screen.findByLabelText("Abrir notificações");
    fireEvent.click(bell);
    const panel = await screen.findByLabelText("Painel de notificações");
    expect(panel.querySelector('a[href="/notifications"]')).toBeTruthy();
    fireEvent.click(bell);
    fireEvent.click(await screen.findByText("Sincronizar Moodle"));
    expect(await screen.findByText("Moodle sincronizado: 2 curso(s), 1 prazo(s) e 3 notificação(ões).")).toBeTruthy();
  });

  it("reruns Moodle diagnostics from the dashboard", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/dashboard")) return json(dashboard);
      if (path.endsWith("/api/moodle/diagnostics")) return json(diagnostics);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText("Verificar Moodle"));

    await waitFor(() => {
      expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/api/moodle/diagnostics")).length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows Moodle diagnostic guidance on error", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/dashboard")) return json(dashboard);
      if (path.endsWith("/api/moodle/diagnostics")) {
        return json({
          ...diagnostics,
          status: "error",
          token_configured: false,
          moodle_available: false,
          user: null,
          courses_count: 0,
          message: "Configure MOODLE_TOKEN no arquivo .env.",
          checks: [{ label: "Token REST", status: "error", detail: "Configure MOODLE_TOKEN no arquivo .env." }],
        });
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Moodle com erro")).toBeTruthy();
    expect((await screen.findAllByText("Configure MOODLE_TOKEN no arquivo .env.")).length).toBeGreaterThan(0);
  });

  it("renders the dedicated Moodle page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/dashboard")) return json(dashboard);
      if (path.endsWith("/api/moodle/diagnostics")) return json(diagnostics);
      if (path.endsWith("/api/tasks")) return json({ tasks: [moodleTask] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/moodle"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Central da integração Moodle: diagnóstico, cursos importados e prazos sincronizados.")).toBeTruthy();
    expect(await screen.findAllByText("Cálculo IV")).toBeTruthy();
    expect(await screen.findByText("Lista de integrais")).toBeTruthy();
  });

  it("renders and manages notifications", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.includes("/api/notifications?status=")) return json({ notifications: [notification] });
      if (path.endsWith("/api/notifications/1/read") && init?.method === "PATCH") return json({ unread_count: 0, changed: 1 });
      if (path.endsWith("/api/notifications/read-all") && init?.method === "POST") return json({ unread_count: 0, changed: 1 });
      if (path.endsWith("/api/notifications/read") && init?.method === "DELETE") return json({ unread_count: 0, changed: 1 });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/notifications"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Prazo vence em 3 dias")).toBeTruthy();
    fireEvent.click((await screen.findAllByText("Não lidas")).find((node) => node.tagName === "BUTTON")!);
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes("status=unread"))).toBe(true));
    fireEvent.click(await screen.findByText("Marcar lida"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/notifications/1/read", expect.objectContaining({ method: "PATCH" })));
    fireEvent.click(await screen.findByText("Limpar lidas"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/notifications/read", expect.objectContaining({ method: "DELETE" })));
  });

  it("configures and manages the smart agenda", async () => {
    const availability = [{ weekday: 0, start_time: "18:00", end_time: "21:00" }];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/agenda/availability") && init?.method === "PUT") return json({ availability });
      if (path.endsWith("/api/agenda/availability")) return json({ availability });
      if (path.endsWith("/api/agenda/suggestions") && init?.method === "POST") return json({ suggestions: [agendaSuggestion] });
      if (path.endsWith("/api/agenda/blocks") && init?.method === "POST") return json({ blocks: [agendaBlock] });
      if (path.endsWith("/api/agenda/blocks/30/complete") && init?.method === "PATCH") return json({ blocks: [{ ...agendaBlock, status: "completed" }] });
      if (path.endsWith("/api/agenda/blocks/30/reschedule") && init?.method === "PATCH") return json({ blocks: [{ ...agendaBlock, start_time: "20:00" }] });
      if (path.includes("/api/agenda?")) return json({ blocks: [agendaBlock] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/agenda"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Agenda inteligente")).toBeTruthy();
    fireEvent.click(await screen.findByText("Salvar disponibilidade"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/agenda/availability", expect.objectContaining({ method: "PUT" })));

    fireEvent.click(screen.getByText("Gerar sugestões"));
    expect(await screen.findByText("Sugestões para confirmar")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Duração Lista de integrais"), { target: { value: "30" } });
    fireEvent.click(screen.getByText("Confirmar 1 bloco(s)"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/agenda/blocks", expect.objectContaining({ method: "POST" })));

    fireEvent.click(screen.getByText("Semana"));
    expect((await screen.findAllByText("Lista de integrais")).length).toBeGreaterThan(0);
    fireEvent.click((await screen.findAllByText("Concluir"))[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/agenda/blocks/30/complete", expect.objectContaining({ method: "PATCH" })));

    fireEvent.click(await screen.findByLabelText("Reagendar Lista de integrais"));
    fireEvent.change(screen.getByLabelText("Novo horário Lista de integrais"), { target: { value: "20:00" } });
    fireEvent.click(screen.getByText("Salvar"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/agenda/blocks/30/reschedule", expect.objectContaining({ method: "PATCH" })));
  });

  it("creates a manual task", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/tasks") && init?.method === "POST") return json({ tasks: [] });
      if (path.endsWith("/api/tasks")) return json({ tasks: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/tasks"]}>
        <App />
      </MemoryRouter>,
    );
    fireEvent.change(await screen.findByPlaceholderText("Título da atividade"), {
      target: { value: "Revisar limites" },
    });
    fireEvent.click(screen.getByText("Adicionar"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/tasks", expect.objectContaining({ method: "POST" }));
    });
  });

  it("opens the chat with a task-specific prompt", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    const conversation = { id: 1, title: "Chat geral", discipline: "general", created_at: "2026-06-02" };
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/tasks")) return json({ tasks: [moodleTask] });
      if (path.endsWith("/api/conversations")) return json({ conversations: [conversation] });
      if (path.endsWith("/api/chat/context")) return json(chatContext);
      if (path.endsWith("/api/conversations/1/messages")) return json({ messages: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/tasks"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Esta semana")).toBeTruthy();
    fireEvent.click(await screen.findByText("Perguntar ao assistente"));
    expect(await screen.findByDisplayValue(/Me ajude a estudar para a atividade/)).toBeTruthy();
  });

  it("sends a chat message and renders the visible chat context", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    const conversation = { id: 1, title: "Chat geral", discipline: "general", created_at: "2026-06-02" };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/conversations")) return json({ conversations: [conversation] });
      if (path.endsWith("/api/chat/context")) return json(chatContext);
      if (path.endsWith("/api/conversations/1/messages") && init?.method === "POST") {
        return json({ answer: "Resposta simulada" });
      }
      if (path.endsWith("/api/conversations/1/messages")) return json({ messages: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Contexto usado pelo assistente")).toBeTruthy();
    expect(await screen.findByText("Cursos Moodle")).toBeTruthy();
    const input = await screen.findByPlaceholderText("Digite sua dúvida...");
    fireEvent.change(input, { target: { value: "Explique derivadas" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/conversations/1/messages",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("renders progress insights", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/insights")) return json(insights);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/progress"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Perguntas feitas")).toBeTruthy();
    expect(await screen.findByText("Limites")).toBeTruthy();
    expect(await screen.findByText("Situação acadêmica")).toBeTruthy();
  });

  it("renders deterministic recommendations", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/profile")) return json({ profile });
      if (path.endsWith("/api/notifications/summary")) return json(notificationSummary);
      if (path.endsWith("/api/insights")) return json(insights);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/recommendations"]}>
        <App />
      </MemoryRouter>,
    );
    expect((await screen.findAllByText("Proteja os próximos prazos")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Plano rápido sugerido")).length).toBeGreaterThan(0);
  });
});
