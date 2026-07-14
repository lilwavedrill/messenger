// Генерация отчёта по ГОСТ 7.32-2017 (для учебной работы).
// Times New Roman 14, интервал 1.5, поля 30/20/20/15 мм, отступ красной строки 12.5 мм.

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageNumber, Footer, Header, TabStopType, TabStopPosition,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  LevelFormat, PageBreak, PageOrientation, ImageRun, convertMillimetersToTwip,
} = require("docx");

// --- helpers ---
const F = "Times New Roman";
const SZ = 28;  // 14pt (docx хранит в half-points)
const SPACING = { line: 360, before: 0, after: 0 };  // 1.5 line
const INDENT_MM = 12.5;

function tr(text, opts = {}) {
  return new TextRun({ text, font: F, size: SZ, ...opts });
}

function p(text, opts = {}) {
  return new Paragraph({
    children: Array.isArray(text) ? text : [tr(text, opts.run || {})],
    spacing: SPACING,
    alignment: opts.align ?? AlignmentType.JUSTIFIED,
    indent: opts.indent === false ? undefined : { firstLine: convertMillimetersToTwip(INDENT_MM) },
    pageBreakBefore: opts.pageBreakBefore || false,
    heading: opts.heading,
  });
}

function h1(text, opts = {}) {
  return new Paragraph({
    children: [tr(text, { bold: true })],
    spacing: { ...SPACING, before: 240, after: 240 },
    alignment: AlignmentType.CENTER,
    heading: HeadingLevel.HEADING_1,
    pageBreakBefore: opts.noBreak ? false : true,
  });
}

function h2(text) {
  return new Paragraph({
    children: [tr(text, { bold: true })],
    spacing: { ...SPACING, before: 240, after: 120 },
    alignment: AlignmentType.LEFT,
    heading: HeadingLevel.HEADING_2,
    indent: { firstLine: convertMillimetersToTwip(INDENT_MM) },
  });
}

function empty() {
  return new Paragraph({ children: [tr(" ")], spacing: SPACING });
}

// Простая ячейка таблицы
function td(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width, type: WidthType.DXA },
    children: [new Paragraph({
      children: [tr(text, opts.bold ? { bold: true } : {})],
      alignment: opts.align ?? AlignmentType.LEFT,
      spacing: { line: 276 },
    })],
    shading: opts.shading ? { type: ShadingType.CLEAR, fill: opts.shading, color: "auto" } : undefined,
  });
}

// --- титульный лист ---
function titlePage() {
  const centered = (text, opts = {}) => new Paragraph({
    children: [tr(text, opts.run || {})],
    alignment: AlignmentType.CENTER,
    spacing: { line: 360, before: opts.before || 0, after: opts.after || 0 },
  });
  return [
    centered("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ", { run: { bold: true } }),
    centered("РОССИЙСКОЙ ФЕДЕРАЦИИ", { run: { bold: true }, after: 120 }),
    centered("_______________________________________________", { after: 120 }),
    centered("(наименование образовательной организации)", { after: 4000 }),

    centered("ОТЧЁТ ПО ПРАКТИКЕ", { run: { bold: true, size: 32 }, after: 240 }),
    centered("по кейсу №1 «Мессенджер»", { run: { size: 30 }, after: 3600 }),

    new Paragraph({
      children: [
        tr("Выполнили: студенты группы _______"),
      ],
      alignment: AlignmentType.LEFT,
      spacing: SPACING,
      indent: { left: convertMillimetersToTwip(80) },
    }),
    new Paragraph({
      children: [tr("________________ / __________________ /")],
      alignment: AlignmentType.LEFT,
      spacing: SPACING,
      indent: { left: convertMillimetersToTwip(80) },
    }),
    new Paragraph({
      children: [tr("________________ / __________________ /")],
      alignment: AlignmentType.LEFT,
      spacing: SPACING,
      indent: { left: convertMillimetersToTwip(80) },
    }),
    empty(),
    new Paragraph({
      children: [tr("Руководитель практики:")],
      alignment: AlignmentType.LEFT,
      spacing: SPACING,
      indent: { left: convertMillimetersToTwip(80) },
    }),
    new Paragraph({
      children: [tr("________________ / __________________ /")],
      alignment: AlignmentType.LEFT,
      spacing: SPACING,
      indent: { left: convertMillimetersToTwip(80) },
    }),

    new Paragraph({
      children: [tr("Москва, 2026 г.")],
      alignment: AlignmentType.CENTER,
      spacing: { before: 3000 },
    }),
  ];
}

// --- реферат ---
function referat() {
  return [
    h1("РЕФЕРАТ"),
    p("Отчёт содержит 25 стр., 6 таблиц, 2 рисунка, 5 источников."),
    empty(),
    p([
      tr("Ключевые слова: ", { bold: true }),
      tr("МЕССЕНДЖЕР, WEBSOCKET, POSTGRESQL, FASTAPI, JWT, РЕАЛЬНОЕ ВРЕМЯ, ЧАТ, ИДЕМПОТЕНТНОСТЬ, СТАТУСЫ ДОСТАВКИ."),
    ]),
    empty(),
    p("Объектом разработки является учебный сервис обмена мгновенными сообщениями (мессенджер) с поддержкой личных и групповых чатов."),
    p("Цель работы — спроектировать и реализовать серверную и клиентскую части мессенджера, обеспечивающие регистрацию и авторизацию пользователей, обмен текстовыми сообщениями в реальном времени, хранение истории и поиск."),
    p("В процессе работы разработаны: схема базы данных, серверное приложение на языке Python (фреймворк FastAPI), реализовано хранение данных в СУБД PostgreSQL, реалтайм-обмен через протокол WebSocket, авторизация через JSON Web Token (JWT), веб-клиент. Дополнительно реализованы статусы доставки сообщений (отправлено, доставлено, прочитано) и идемпотентность отправки."),
    p("Разработанное решение может быть использовано как основа для дальнейших исследований в области распределённых систем обмена сообщениями."),
  ];
}

// --- содержание ---
function toc() {
  const dot = ".".repeat(80);
  const item = (title, page) => new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX, leader: "dot" }],
    children: [tr(title), tr("\t" + page)],
    spacing: SPACING,
  });
  return [
    h1("СОДЕРЖАНИЕ"),
    item("Введение", "4"),
    item("1 Аналитическая часть", "5"),
    item("1.1 Предметная область", "5"),
    item("1.2 Анализ функциональных требований", "6"),
    item("1.3 Анализ нефункциональных требований", "7"),
    item("2 Проектная часть", "8"),
    item("2.1 Архитектура системы", "8"),
    item("2.2 Структура базы данных", "10"),
    item("2.3 Модель авторизации и роли доступа", "13"),
    item("2.4 Спецификация API", "14"),
    item("3 Практическая реализация", "16"),
    item("3.1 Стек технологий", "16"),
    item("3.2 Реализация функциональных требований", "17"),
    item("3.3 Тестирование", "20"),
    item("3.4 Инструкция по запуску", "22"),
    item("Заключение", "23"),
    item("Список использованных источников", "24"),
    item("Приложение А. ER-диаграмма базы данных", "25"),
  ];
}

// --- введение ---
function intro() {
  return [
    h1("ВВЕДЕНИЕ"),
    p("Сервисы мгновенного обмена сообщениями стали одним из наиболее востребованных классов программного обеспечения. По данным аналитических агентств, ежедневно через мессенджеры пересылаются десятки миллиардов сообщений. Проектирование подобных систем требует решения ряда нетривиальных задач: обеспечение низкой задержки при доставке, гарантий надёжности, защиты от повторных доставок, масштабирования на большое число пользователей."),
    p("В рамках практической работы поставлена задача разработать учебную реализацию мессенджера с базовым набором функций: регистрацией пользователей, ведением личных и групповых переписок, реалтайм-обменом сообщениями, хранением истории и поиском. Работа выполнена по кейсу № 1 практики VK Education."),
    p([tr("Цель работы: ", { bold: true }), tr("разработать серверную и клиентскую части учебного мессенджера, удовлетворяющие функциональным и нефункциональным требованиям технического задания.")]),
    p([tr("Задачи работы:", { bold: true })]),
    p("— провести анализ предметной области и требований технического задания;", { indent: false }),
    p("— спроектировать схему базы данных, обеспечивающую хранение пользователей, чатов и сообщений;", { indent: false }),
    p("— разработать серверное приложение с REST-API и WebSocket-эндпоинтом;", { indent: false }),
    p("— реализовать модель авторизации на основе JWT;", { indent: false }),
    p("— разработать веб-клиент для демонстрации работы сервиса;", { indent: false }),
    p("— провести функциональное тестирование по сценариям.", { indent: false }),
    p([tr("Объект исследования: ", { bold: true }), tr("процесс обмена сообщениями между пользователями в реальном времени.")]),
    p([tr("Предмет исследования: ", { bold: true }), tr("программные средства и архитектурные решения для организации мгновенного обмена сообщениями.")]),
  ];
}

// --- гл. 1 ---
function chapter1() {
  return [
    h1("1 АНАЛИТИЧЕСКАЯ ЧАСТЬ"),
    h2("1.1 Предметная область"),
    p("Мессенджеры — класс приложений, обеспечивающих обмен текстовыми (и, как правило, мультимедийными) сообщениями между пользователями в режиме, близком к реальному времени. Ключевое отличие от классической электронной почты — доставка сообщения адресату в течение долей секунды после отправки и «онлайн-присутствие» участников."),
    p("Типовой мессенджер состоит из следующих логических компонентов:"),
    p("— клиентские приложения (мобильные, десктопные, веб);", { indent: false }),
    p("— серверная часть, принимающая и рассылающая сообщения;", { indent: false }),
    p("— база данных для хранения истории;", { indent: false }),
    p("— система авторизации;", { indent: false }),
    p("— (опционально) объектное хранилище для вложений.", { indent: false }),
    p("С точки зрения пользователя мессенджер должен обеспечивать: возможность зарегистрироваться и войти в систему, найти собеседника, обмениваться с ним сообщениями с минимальной задержкой, видеть историю переписки, знать о том, доставлено и прочитано ли отправленное сообщение."),

    h2("1.2 Анализ функциональных требований"),
    p("На основании технического задания, полученного в рамках практики VK Education (кейс № 1), выделены следующие функциональные требования к разрабатываемому сервису (таблица 1.1)."),
    empty(),
    p("Таблица 1.1 — Функциональные требования", { align: AlignmentType.LEFT, indent: false }),
    tableFuncReqs(),
    empty(),

    h2("1.3 Анализ нефункциональных требований"),
    p("Нефункциональные требования определяют свойства системы, не связанные напрямую с бизнес-функциональностью, но существенные для её эксплуатации:"),
    p("— отзывчивость: доставка сообщения от отправителя к получателю не более чем за 200 мс;", { indent: false }),
    p("— надёжность: при обрыве соединения сообщения не должны теряться; повторная отправка не должна создавать дубликатов;", { indent: false }),
    p("— безопасность: пароли пользователей должны храниться только в виде хэшей, все защищённые эндпоинты — требовать валидный токен доступа;", { indent: false }),
    p("— порядок сообщений: сообщения в рамках одного диалога должны отображаться в правильном хронологическом порядке;", { indent: false }),
    p("— наблюдаемость: все значимые действия пользователей должны фиксироваться в журнале аудита.", { indent: false }),
  ];
}

function tableFuncReqs() {
  const cols = [1500, 5000, 3000];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("№", "Требование", "Тип", true),
      row("ФТ-1", "Регистрация и вход пользователя", "обязательное"),
      row("ФТ-2", "Личные чаты (1-на-1)", "обязательное"),
      row("ФТ-3", "Групповые чаты с названием", "обязательное"),
      row("ФТ-4", "Отправка и получение сообщений в реальном времени", "обязательное"),
      row("ФТ-5", "История сообщений с пагинацией", "обязательное"),
      row("ФТ-6", "Управление участниками чата (только владельцем)", "обязательное"),
      row("ФТ-7", "Поиск по сообщениям в рамках чата", "обязательное"),
      row("ФТ-8", "Статусы доставки сообщений", "дополнительное"),
      row("ФТ-9", "Идемпотентность отправки", "дополнительное"),
    ],
  });
}

// --- гл. 2 ---
function chapter2() {
  return [
    h1("2 ПРОЕКТНАЯ ЧАСТЬ"),
    h2("2.1 Архитектура системы"),
    p("Разработанное решение построено по трёхзвенной архитектуре и включает следующие компоненты:"),
    p("— клиентское приложение — одностраничный веб-документ (HTML/CSS/JavaScript), взаимодействующий с сервером через REST-API и WebSocket;", { indent: false }),
    p("— сервер приложения — Python-программа на базе фреймворка FastAPI, реализующая обработку HTTP-запросов, аутентификацию, работу с базой данных и рассылку сообщений подписчикам через WebSocket;", { indent: false }),
    p("— СУБД PostgreSQL — хранит данные пользователей, чатов, сообщений, статусов доставки, а также журнал аудита.", { indent: false }),
    p("Взаимодействие компонентов схематически представлено на рисунке 2.1."),
    p("Рисунок 2.1 — Архитектура системы (см. приложение А для ER-диаграммы БД)", { align: AlignmentType.CENTER, indent: false, run: { italics: true } }),
    p("В качестве транспорта для реалтайм-обмена сообщениями выбран протокол WebSocket. Данный выбор обоснован тремя факторами: (а) протокол работает поверх HTTP и не требует дополнительной инфраструктуры; (б) поддерживается нативно всеми современными браузерами; (в) обеспечивает простую двустороннюю связь между клиентом и сервером."),
    p("Отправка сообщения реализована по гибридной схеме: клиент отправляет сообщение через REST (`POST /chats/{id}/messages`), сервер записывает его транзакционно в базу данных, после чего широковещательно рассылает событие подписчикам через WebSocket. Такой подход обеспечивает надёжность: даже при обрыве WebSocket-соединения сообщение уже сохранено в БД."),

    h2("2.2 Структура базы данных"),
    p("Схема базы данных нормализована до третьей нормальной формы и включает шесть таблиц (таблица 2.1). Полная ER-диаграмма приведена в приложении А."),
    empty(),
    p("Таблица 2.1 — Основные сущности базы данных", { align: AlignmentType.LEFT, indent: false }),
    tableEntities(),
    empty(),
    p("Для оптимизации типовых операций созданы следующие индексы:"),
    p("— составной индекс (chat_id, id DESC) на таблице messages — обеспечивает эффективную пагинацию сообщений «вверх» с временем работы O(log n);", { indent: false }),
    p("— GIN-индекс to_tsvector('russian', text) на таблице messages — используется для полнотекстового поиска;", { indent: false }),
    p("— индекс (user_id) на таблице chat_members — ускоряет выборку чатов пользователя.", { indent: false }),
    empty(),
    p("Ниже приведены примеры типовых SQL-запросов, используемых в приложении."),
    p([tr("Запрос списка чатов пользователя (JOIN двух таблиц):", { italics: true })]),
    p("SELECT c.* FROM chats c JOIN chat_members cm ON cm.chat_id = c.id WHERE cm.user_id = :user_id ORDER BY c.created_at DESC;", { indent: false, run: { font: "Courier New", size: 22 } }),
    p([tr("История сообщений с пагинацией:", { italics: true })]),
    p("SELECT * FROM messages WHERE chat_id = :chat_id AND id < :before_id ORDER BY id DESC LIMIT 50;", { indent: false, run: { font: "Courier New", size: 22 } }),
    p([tr("Агрегированная статистика по авторам (GROUP BY, подзапрос):", { italics: true })]),
    p("SELECT u.username, COUNT(*) AS cnt FROM messages m JOIN users u ON u.id = m.sender_id WHERE m.chat_id = (SELECT id FROM chats WHERE title = 'General' LIMIT 1) GROUP BY u.username ORDER BY cnt DESC;", { indent: false, run: { font: "Courier New", size: 22 } }),

    h2("2.3 Модель авторизации и роли доступа"),
    p("Для аутентификации пользователей выбрана схема на основе JSON Web Token (JWT). Процесс входа устроен следующим образом:"),
    p("1) пользователь передаёт логин и пароль на эндпоинт POST /auth/login;", { indent: false }),
    p("2) сервер извлекает из БД сохранённый хэш пароля и сравнивает его с введённым паролем с помощью алгоритма bcrypt;", { indent: false }),
    p("3) в случае успеха формируется JWT-токен, содержащий идентификатор пользователя и время истечения (24 часа);", { indent: false }),
    p("4) токен возвращается клиенту, который передаёт его в заголовке Authorization: Bearer <token> для всех защищённых эндпоинтов.", { indent: false }),
    p("Пароли пользователей никогда не хранятся в открытом виде. При регистрации выполняется однонаправленное преобразование пароля с использованием алгоритма bcrypt и случайной соли, что делает невозможным восстановление исходного пароля даже при компрометации базы данных."),
    empty(),
    p("В системе реализованы три роли, действующие внутри каждого чата (таблица 2.2). Роль присваивается пользователю в момент добавления его в чат."),
    empty(),
    p("Таблица 2.2 — Роли и права доступа", { align: AlignmentType.LEFT, indent: false }),
    tableRoles(),

    h2("2.4 Спецификация API"),
    p("Сервер предоставляет REST-интерфейс, документированный по стандарту OpenAPI 3.0. Полная интерактивная спецификация доступна по адресу /docs после запуска сервера. Основные эндпоинты приведены в таблице 2.3."),
    empty(),
    p("Таблица 2.3 — Основные эндпоинты API", { align: AlignmentType.LEFT, indent: false }),
    tableApi(),
  ];
}

function tableEntities() {
  const cols = [2500, 3000, 4000];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("Таблица", "Первичный ключ", "Назначение", true),
      row("users", "id (BIGSERIAL)", "Пользователи системы"),
      row("chats", "id (BIGSERIAL)", "Личные и групповые чаты"),
      row("chat_members", "(chat_id, user_id)", "Участники чата и их роли"),
      row("messages", "id (BIGSERIAL)", "Сообщения"),
      row("message_status", "(message_id, user_id)", "Статусы доставки сообщений"),
      row("audit_log", "id (BIGSERIAL)", "Журнал действий пользователей"),
    ],
  });
}

function tableRoles() {
  const cols = [2500, 2500, 2500, 2500];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, d, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(d, { width: cols[3], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("Роль", "Чтение", "Отправка", "Управление участниками", true),
      row("reader (читатель)", "да", "нет", "нет"),
      row("writer (участник)", "да", "да", "нет"),
      row("owner (владелец)", "да", "да", "да"),
    ],
  });
}

function tableApi() {
  const cols = [1500, 4500, 4000];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("Метод", "Путь", "Назначение", true),
      row("POST", "/auth/register", "Регистрация нового пользователя"),
      row("POST", "/auth/login", "Аутентификация, получение JWT"),
      row("GET", "/chats", "Список чатов пользователя"),
      row("POST", "/chats", "Создание нового чата"),
      row("POST", "/chats/{id}/members", "Добавление участника (только owner)"),
      row("DELETE", "/chats/{id}/members/{uid}", "Удаление участника"),
      row("GET", "/chats/{id}/messages", "Получение истории сообщений"),
      row("POST", "/chats/{id}/messages", "Отправка сообщения"),
      row("GET", "/chats/{id}/search", "Поиск по сообщениям чата"),
      row("WS", "/ws/{chat_id}", "WebSocket-подписка на события чата"),
    ],
  });
}

// --- гл. 3 ---
function chapter3() {
  return [
    h1("3 ПРАКТИЧЕСКАЯ РЕАЛИЗАЦИЯ"),
    h2("3.1 Стек технологий"),
    p("В качестве языка программирования выбран Python версии 3.13. Данный выбор обоснован простотой синтаксиса, богатой экосистемой библиотек для веб-разработки и рекомендациями преподавателя."),
    p("Для реализации серверной части использован фреймворк FastAPI. FastAPI поддерживает асинхронное программирование, автоматическую генерацию OpenAPI-документации, встроенную валидацию входных данных через Pydantic и обработку WebSocket-соединений в рамках одного процесса."),
    p("В качестве СУБД выбрана PostgreSQL версии 14 — реляционная база данных с полной поддержкой транзакций, продвинутыми возможностями индексирования (в том числе GIN-индексов для полнотекстового поиска) и типа данных JSONB для журнала аудита. Для работы с БД из Python использована библиотека SQLAlchemy 2.x в режиме синхронной сессии."),
    p("Хэширование паролей выполняется библиотекой passlib с использованием алгоритма bcrypt. Генерация и валидация JWT-токенов выполняется библиотекой python-jose."),
    p("Клиентская часть реализована как одностраничное веб-приложение без использования JavaScript-фреймворков и сборщиков — весь код умещается в одном HTML-файле, что упрощает развёртывание и демонстрацию."),

    h2("3.2 Реализация функциональных требований"),
    p("В таблице 3.1 приведено соответствие функциональных требований технического задания и элементов реализации."),
    empty(),
    p("Таблица 3.1 — Реализация функциональных требований", { align: AlignmentType.LEFT, indent: false }),
    tableImpl(),
    empty(),
    p("Отдельного внимания заслуживает механизм идемпотентности. При отправке сообщения клиент может передать необязательный параметр client_msg_id — уникальный идентификатор в формате UUID, сгенерированный на стороне клиента. Данный идентификатор сохраняется в соответствующем поле таблицы messages. Уникальное ограничение UNIQUE (chat_id, client_msg_id) на уровне базы данных гарантирует, что повторная отправка одного и того же сообщения (например, при ретрае после ошибки сети) не создаст дубликата: сервер обнаружит существующую запись и вернёт клиенту её данные."),
    p("Реализация статусов доставки построена на отдельной таблице message_status, содержащей по одной записи на каждую пару (сообщение, получатель). При отправке сообщения для всех участников чата создаются записи со статусом sent. При получении сообщения клиент отправляет по WebSocket событие ack — статус обновляется на delivered. При отображении сообщения на экране (открытии соответствующего чата) клиент отправляет событие read — статус обновляется на read. Обновления статусов широковещательно рассылаются всем подписчикам чата, что позволяет отправителю в реальном времени видеть «одну галочку», «две галочки», «две синих галочки»."),

    h2("3.3 Тестирование"),
    p("Проведено функциональное тестирование по девяти сценариям (таблица 3.2). Тесты выполнялись как сквозные интеграционные проверки — с реальной СУБД и реальным HTTP/WebSocket-сервером."),
    empty(),
    p("Таблица 3.2 — Сценарии тестирования", { align: AlignmentType.LEFT, indent: false }),
    tableTests(),

    h2("3.4 Инструкция по запуску"),
    p("Для запуска приложения требуется macOS или Linux, Python 3.11 или новее, PostgreSQL 14 или новее. Последовательность действий:"),
    p("1) склонировать репозиторий проекта;", { indent: false }),
    p("2) создать базу данных: psql -U postgres -c \"CREATE DATABASE messenger;\"", { indent: false, run: { font: "Courier New", size: 22 } }),
    p("3) применить схему: psql -U postgres -d messenger -f backend/schema.sql", { indent: false, run: { font: "Courier New", size: 22 } }),
    p("4) создать виртуальное окружение и установить зависимости:", { indent: false }),
    p("cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt", { indent: false, run: { font: "Courier New", size: 22 } }),
    p("5) настроить файл .env (переменные DATABASE_URL и JWT_SECRET);", { indent: false }),
    p("6) запустить сервер: .venv/bin/uvicorn app.main:app --port 8000", { indent: false, run: { font: "Courier New", size: 22 } }),
    p("После запуска доступны следующие адреса:"),
    p("— веб-клиент: http://127.0.0.1:8000/app/;", { indent: false }),
    p("— документация API (Swagger UI): http://127.0.0.1:8000/docs;", { indent: false }),
    p("— проверка работоспособности: http://127.0.0.1:8000/healthz.", { indent: false }),
  ];
}

function tableImpl() {
  const cols = [1200, 5500, 3500];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("№", "Реализация", "Компонент проекта", true),
      row("ФТ-1", "Регистрация: POST /auth/register; вход: POST /auth/login", "app/routes_auth.py"),
      row("ФТ-2", "Создание чата с type='direct'", "app/routes_chats.py"),
      row("ФТ-3", "Создание чата с type='group' и указанием title", "app/routes_chats.py"),
      row("ФТ-4", "Транзакционная запись + широковещание через WebSocket", "app/routes_ws.py, app/hub.py"),
      row("ФТ-5", "GET /chats/{id}/messages с параметром before_id", "app/routes_messages.py"),
      row("ФТ-6", "Проверка роли owner при добавлении/удалении участников", "app/routes_chats.py"),
      row("ФТ-7", "GET /chats/{id}/search — поиск по подстроке текста", "app/routes_messages.py"),
      row("ФТ-8", "Таблица message_status, WS-события ack и read", "app/routes_ws.py"),
      row("ФТ-9", "Уникальный ключ (chat_id, client_msg_id)", "app/models.py, schema.sql"),
    ],
  });
}

function tableTests() {
  const cols = [800, 4500, 4500];
  const total = cols.reduce((a, b) => a + b, 0);
  const row = (a, b, c, header = false) => new TableRow({
    children: [
      td(a, { width: cols[0], bold: header, align: AlignmentType.CENTER, shading: header ? "E5E7EB" : undefined }),
      td(b, { width: cols[1], bold: header, shading: header ? "E5E7EB" : undefined }),
      td(c, { width: cols[2], bold: header, shading: header ? "E5E7EB" : undefined }),
    ],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: cols,
    rows: [
      row("№", "Сценарий", "Ожидаемый результат", true),
      row("1", "Регистрация двух пользователей, вход", "Оба получают JWT-токены; статус 201/200"),
      row("2", "Создание группового чата с одним участником", "Статус 201; в БД появляются записи в chats и chat_members"),
      row("3", "Отправка трёх сообщений от одного пользователя", "Все сохранены в БД; второй пользователь получает push через WebSocket"),
      row("4", "Запрос истории сообщений", "Возвращается список сообщений в хронологическом порядке"),
      row("5", "Поиск по подстроке в тексте сообщений", "Возвращаются только релевантные сообщения"),
      row("6", "Отправка сообщения с пустым текстом", "Статус 422 (валидация не пройдена)"),
      row("7", "Запрос без Authorization заголовка", "Статус 401"),
      row("8", "Отправка в несуществующий чат", "Статус 404"),
      row("9", "Полный цикл статуса: отправлено → доставлено → прочитано", "Отправитель видит смену статуса через WebSocket-события"),
    ],
  });
}

// --- заключение ---
function conclusion() {
  return [
    h1("ЗАКЛЮЧЕНИЕ"),
    p("В ходе выполнения практической работы решены все поставленные задачи. Разработан учебный сервис обмена мгновенными сообщениями, отвечающий функциональным и нефункциональным требованиям технического задания."),
    p("Проведён анализ предметной области, выделены и формализованы функциональные (7 обязательных, 2 дополнительных) и нефункциональные требования. Спроектирована нормализованная схема базы данных из шести таблиц, снабжённая необходимыми индексами для эффективного выполнения типовых запросов."),
    p("Реализовано серверное приложение на языке Python с использованием фреймворка FastAPI. Реалтайм-обмен сообщениями организован через протокол WebSocket с in-memory реестром активных подключений. Аутентификация пользователей выполнена на основе JWT-токенов, пароли хранятся в виде bcrypt-хэшей. Реализованы три роли доступа внутри чата: reader, writer, owner."),
    p("Дополнительно реализована функциональность, выходящая за рамки минимальных требований: система статусов доставки сообщений (отправлено, доставлено, прочитано) с уведомлениями в реальном времени и механизм идемпотентности отправки для защиты от повторных сообщений при ретраях сетевых запросов."),
    p("Разработан веб-клиент для демонстрации работы сервиса. Проведено функциональное тестирование по девяти сценариям, включая проверку негативных случаев."),
    p("Возможные направления развития проекта: замена in-memory реестра подключений на брокер сообщений (Redis Streams или NATS JetStream) для масштабирования на несколько инстансов сервера; добавление поддержки вложений через объектное хранилище S3; реализация E2E-шифрования переписки."),
  ];
}

// --- источники ---
function references() {
  const src = [
    "1. FastAPI documentation [Электронный ресурс]. — URL: https://fastapi.tiangolo.com/ (дата обращения: 13.07.2026).",
    "2. PostgreSQL 14 Documentation [Электронный ресурс]. — URL: https://www.postgresql.org/docs/14/ (дата обращения: 13.07.2026).",
    "3. Fette I., Melnikov A. RFC 6455: The WebSocket Protocol [Электронный ресурс]. — URL: https://datatracker.ietf.org/doc/html/rfc6455 (дата обращения: 13.07.2026).",
    "4. Jones M., Bradley J., Sakimura N. RFC 7519: JSON Web Token (JWT) [Электронный ресурс]. — URL: https://datatracker.ietf.org/doc/html/rfc7519 (дата обращения: 13.07.2026).",
    "5. Provos N., Mazières D. A Future-Adaptable Password Scheme // Proceedings of 1999 USENIX Annual Technical Conference. — 1999. — С. 81—92.",
  ];
  return [
    h1("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"),
    ...src.map(s => p(s, { indent: false })),
  ];
}

// --- приложение ---
function appendix() {
  const imagePath = "docs/er.png";
  const imgBuf = fs.existsSync(imagePath) ? fs.readFileSync(imagePath) : null;
  const items = [
    h1("ПРИЛОЖЕНИЕ А"),
    new Paragraph({
      children: [tr("(обязательное)", { italics: true })],
      alignment: AlignmentType.CENTER,
      spacing: SPACING,
    }),
    new Paragraph({
      children: [tr("ER-диаграмма базы данных", { bold: true })],
      alignment: AlignmentType.CENTER,
      spacing: { ...SPACING, before: 240, after: 240 },
    }),
  ];
  if (imgBuf) {
    items.push(new Paragraph({
      children: [new ImageRun({ data: imgBuf, transformation: { width: 620, height: 340 }, type: "png" })],
      alignment: AlignmentType.CENTER,
      spacing: SPACING,
    }));
  }
  items.push(p("Рисунок А.1 — ER-диаграмма базы данных мессенджера", { align: AlignmentType.CENTER, indent: false, run: { italics: true } }));
  return items;
}

// --- собираем документ ---
const doc = new Document({
  creator: "",
  styles: {
    default: {
      document: {
        run: { font: F, size: SZ },
        paragraph: { spacing: SPACING },
      },
    },
  },
  sections: [
    // титульный лист — без нумерации и без колонтитулов
    {
      properties: {
        page: {
          margin: {
            top: convertMillimetersToTwip(20),
            right: convertMillimetersToTwip(15),
            bottom: convertMillimetersToTwip(20),
            left: convertMillimetersToTwip(30),
          },
        },
        titlePage: true,
      },
      children: titlePage(),
    },
    // остальные разделы — с нумерацией
    {
      properties: {
        page: {
          margin: {
            top: convertMillimetersToTwip(20),
            right: convertMillimetersToTwip(15),
            bottom: convertMillimetersToTwip(20),
            left: convertMillimetersToTwip(30),
          },
          pageNumbers: { start: 2 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [tr(""), new TextRun({ children: [PageNumber.CURRENT], font: F, size: SZ })],
          })],
        }),
      },
      children: [
        ...referat(),
        ...toc(),
        ...intro(),
        ...chapter1(),
        ...chapter2(),
        ...chapter3(),
        ...conclusion(),
        ...references(),
        ...appendix(),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("docs/report.docx", buf);
  console.log("OK, wrote docs/report.docx");
});
