# 0017: Раздельные страницы входа

Branch: `task/separate-login-entrypoints`
Status: In progress

## Goal

Разделить вход ведущего и игрока по разным URL, чтобы рассылаемая игрокам ссылка никогда не показывала форму или переключатель admin-login.

## Decisions

- `/play` показывает только ввод имени игрока; `/admin` показывает только пароль ведущего.
- `/` и неизвестные frontend-пути канонизируются в `/play`; завершающий slash у `/play/` и `/admin/` убирается без перезагрузки.
- Между entrypoint-формами нет ссылок, вкладок или переключателей. Ведущий хранит `/admin` отдельно, игрокам отправляется `/play`.
- Entry point ограничивает session restore: `/play` читает только player token, `/admin` — только admin token. Токен другой роли не удаляется, но на этом route не используется.
- Logout и истечение сессии оставляют браузер на текущем route.
- Оба entrypoint используют прежний React runtime, Socket.IO singleton и backend auth events. Разделение URL — UX-граница, не замена password/token authorization.
- Для двух статичных routes не добавляется router dependency. Pure route helper выбирает entrypoint и canonical path до рендера `App`.
- Vite development/preview должны поддерживать прямое открытие/refresh SPA routes. Будущий production reverse proxy обязан направлять `/`, `/play` и `/admin` на frontend `index.html`.
- Обе формы оставлены без поясняющего подзаголовка и видимых field labels: назначение поля понятно из placeholder, а скрытые labels сохранены для accessibility.
- Все экраны ведущего — login, lobby и основная игра — визуально отличаются от player-view тёмно-индиговым фоном; структура и навигация при этом остаются общими.
- В пользовательских сообщениях и заголовках используется игровая роль «ведущий», а не техническое «администратор»/`Admin`.

## Out of scope

- Backend endpoints для HTML-login, разные frontend bundles/domains, приглашения с секретом в URL, изменение admin/player token lifecycle, production reverse proxy и access control по самому pathname.

## Verification plan

- Pure tests для route resolution/canonicalization и role-scoped session restore.
- Frontend test suite и production build.
- Browser smoke: прямой `/play` и `/admin`, `/` redirect, refresh, login, reconnect, logout и отсутствие чужой формы.

## Local verification

- `python3 -W error -m pytest -q`: 189 tests passed (backend behavior unchanged).
- `npm test`: 39 tests across 9 test files passed.
- `npm run build`: passed.
- Temporary Vite dev server returned the SPA entry document with HTTP 200 for `/`, `/play`, `/play/`, `/admin`, `/admin/`, and an unknown path; client route tests cover their canonical destinations.
