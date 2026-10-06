# Android Porting Checklist

Use this checklist to keep the Android replica complete.

## Source Inventory

- iOS app targets, app entry points, `Info.plist`, entitlements, assets, localized strings, bundled JSON, vendor packages, and build settings.
- Requirement documents and design notes near the iOS or server project.
- Backend routes, serializers/schemas, models, permissions, auth middleware, migrations, streaming endpoints, upload handlers, and version endpoints.
- Existing generated API docs, OpenAPI specs, Postman collections, or markdown API notes.

## Product Parity

- App launch, onboarding, login, logout, account switching, token refresh, account deletion, and device binding.
- Main tabs, nested navigation, modal sheets/dialogs, detail pages, forms, search, filters, sorting, and pagination.
- Chat, AI configuration, model selection, tool calls, streaming responses, attachments, retries, and cancellation when present.
- Medical/health records, family/member binding, sharing, file manager, task system, app version checks, and nutrition/medicine flows when present.
- Empty, loading, disabled, validation, permission-denied, offline, server-error, and destructive-confirmation states.
- Push notifications, background sync, deep links, share extension behavior, and file/document picking.

## Backend Contract Parity

- HTTP method, path, query parameters, body shape, headers, auth, content type, status codes, and error payloads.
- Date/time zones, timestamp precision, decimal precision, enum strings, nullable fields, default values, and pagination cursors.
- Multipart field names, upload limits, accepted MIME types, download filenames, and signed URL behavior.
- SSE/WebSocket event names, event payload schemas, reconnection rules, heartbeat handling, and cancellation semantics.
- Versioning, feature flags, app update endpoints, and server-side capability switches.

## Android Architecture

- Existing Android baseline: read `settings.gradle(.kts)`, `docs/architecture.md`, `docs/module-dependencies.md`, `gradle/libs.versions.toml`, `build-logic`, manifest, navigation, DI modules, and active requirement docs before changing code.
- Existing Spark-style baseline: preserve `app`, `foundation`, `core:*`, `features:*`, and convention plugins; implement parity in the nearest established module.
- `data` or infrastructure layer: existing networking client such as Ktor or Retrofit, DTOs, repositories, persistence, mappers.
- `domain`: optional use cases and domain models for complex business logic.
- `ui`: Compose screens, navigation graph, ViewModels, UI state, reusable components.
- `core`: networking, auth/session, logging, error mapping, time/date utilities, secure storage.

Keep the architecture smaller if the app is small. Add modules only when they reduce real complexity.

## Existing Android Baseline Parity

- Compare iOS feature files against Android `features/*` and `core/*` modules to find missing screens, missing state branches, API mismatches, and placeholder repositories.
- Prefer completion over replacement: keep existing ViewModel state names, route names, DI bindings, Ktor/serialization choices, and resource organization unless they conflict with iOS/server truth.
- Treat existing Android requirement documents and `ANDROID-*IOS-ALIGN*` docs as a backlog. Reconcile their claims against source code before declaring a feature complete.
- Confirm Android localized strings are present for user-visible text and do not hardcode copy in Compose.

## Verification

- Build: `./gradlew assembleDebug`.
- Tests: `./gradlew testDebugUnitTest` and instrumentation tests when available.
- Serialization tests for every nontrivial API response and streaming event.
- Manual parity pass against iOS for each shipped feature.
- Backend smoke test for login, refresh, core list/detail flows, uploads, chat/streaming, and account deletion where applicable.

## Delivery Notes

In the final response, report:

- Android project path.
- Implemented feature areas.
- Important iOS/server files used as source of truth.
- Existing Android baseline files or docs preserved.
- Build/test commands run and results.
- Known gaps or assumptions that still need product confirmation.
