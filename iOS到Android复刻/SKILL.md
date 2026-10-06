---
name: replicate-ios-to-android
description: Build, update, or complete an Android client by faithfully porting an existing iOS app and its server contracts. Use when Codex is given a backend project, an iOS client, and either no Android client or an incomplete Android client, or when asked to replicate iOS screens, navigation, API behavior, local models, assets, permissions, login flows, chat/medical/health features, or product requirements into Kotlin/Jetpack Compose or a native Android project.
---

# Replicate iOS To Android

## Mission

Port the iOS app into an Android app that matches product behavior, backend contracts, screen flows, data semantics, error handling, and release readiness. Treat the iOS client as the product source of truth, the server project as the API and data-contract source of truth, and any existing Android project as the implementation baseline to preserve and complete.

## Default Stack

When no Android project exists, use Kotlin, Gradle, Jetpack Compose, Material 3, Kotlin coroutines, Retrofit/OkHttp or Ktor, kotlinx.serialization or Moshi, Room/DataStore when persistence is needed, Hilt when dependency injection is useful, and Coil for images.

When an Android project already exists, follow its stack, modules, conventions, naming, build logic, dependency injection, networking client, persistence choices, localization strategy, and test layout. Do not replace Ktor with Retrofit, change module boundaries, or rewrite build logic unless the existing implementation is broken and the user asked for that level of change.

Prefer native Android implementation over WebView unless the iOS app itself embeds web screens for the same feature.

## Workflow

1. Locate source projects.
   - Identify the iOS app root by `.xcodeproj`, `.xcworkspace`, `Package.swift`, `Info.plist`, app target folders, Swift files, assets, and requirement documents.
   - Identify the backend root by framework markers such as `manage.py`, `urls.py`, `settings.py`, OpenAPI specs, route files, controllers, serializers, models, migrations, or API docs.
   - Identify the Android root by `settings.gradle(.kts)`, `build.gradle(.kts)`, `gradle/libs.versions.toml`, `AndroidManifest.xml`, `app`, `core`, `features`, `build-logic`, Kotlin files, and Android requirement documents.
   - If multiple iOS projects exist, choose the one most directly paired with the backend or ask only when the choice is genuinely ambiguous.

2. Run the audit script when useful.
   - Execute `scripts/audit_sources.py --ios <ios-root> --server <server-root> --android <android-root> --out <report.md>` when an Android baseline exists.
   - Omit `--android` only when creating a new Android project from scratch.
   - Read the report before implementation. Use it to drive the migration backlog, not as a substitute for reading source files.

3. Build the product inventory.
   - Enumerate screens, navigation routes, tabs, modal flows, empty states, loading states, error states, permissions, notifications, background tasks, sharing, file upload/download, and offline behavior.
   - Map SwiftUI/UIKit screens to Compose screens. Preserve user-visible labels, ordering, validation rules, and conditional states unless Android conventions require a small adjustment.
   - Extract API calls from iOS networking code and confirm them against backend routes, serializers, request/response schemas, auth requirements, pagination, streaming/SSE/WebSocket behavior, and upload formats.
   - Extract local models, cache behavior, encryption/keychain usage, app settings, feature flags, AI model configuration, and bundled JSON/assets.

4. Create or update the Android project.
   - If an Android project exists, inspect its architecture docs, module dependency docs, requirement docs, Gradle settings, version catalog, convention plugins, app manifest, navigation graph, DI modules, networking abstractions, localization resources, and tests before editing.
   - Preserve existing modules and implement missing parity inside the closest established module. For a Spark-style project, expect `app`, `foundation`, `core:*`, `features:*`, and `build-logic`.
   - If no Android project exists, create a conventional Gradle Android app at the requested location, usually `<workspace>/AndroidClient` or `<product-name>-android`.
   - Set package name, minSdk, targetSdk, app name, permissions, signing placeholders, build variants, ProGuard/R8 rules, and network security config from iOS/server needs.
   - Keep modules simple unless the app is large enough to justify `core`, `data`, `domain`, and `feature-*` modules.

5. Implement feature slices end to end.
   - For each iOS flow, implement Android UI, ViewModel/state holder, repository, API client, models, persistence, and navigation together.
   - Match server contracts exactly: endpoints, methods, headers, auth refresh, content types, date/time formats, enum strings, optional/null behavior, pagination, SSE/WebSocket event shapes, and multipart field names.
   - Preserve security requirements from iOS and backend, including token storage, encrypted local data, TLS/certificate behavior, privacy permissions, and account deletion/deactivation flows.

6. Validate against iOS and backend.
   - Build the Android project with Gradle.
   - Run unit tests and any available instrumentation tests.
   - Start or inspect backend tests when practical, and verify Android API calls against real routes or documented contracts.
   - Compare each implemented Android screen against the iOS source for navigation, state, copy, visible data, and edge cases.

## Porting Rules

- Do not invent missing product behavior. Infer from iOS, backend, and requirement docs; document any unresolved gaps.
- Do not copy iOS-only implementation details blindly. Translate behavior into Android-native patterns.
- Keep API schema names and enum values stable unless backend code proves they differ.
- Keep UI density and hierarchy faithful to iOS while respecting Android ergonomics.
- Prefer real backend integration over mocked data once the contract is known.
- Add focused tests for serialization, repository behavior, auth/session logic, validators, and nontrivial ViewModel state transitions.
- Avoid broad refactors in iOS or server projects unless the user explicitly asks for them.
- In an existing Android baseline, treat docs named like `ANDROID-*IOS-ALIGN*`, architecture notes, and feature requirement documents as active constraints. Update them only when needed to keep implementation status honest.

## Common Source Patterns

- SwiftUI `View` or UIKit `ViewController` -> Compose screen plus state holder.
- Swift `ObservableObject`, `@State`, `@Published`, async tasks -> ViewModel with immutable UI state and coroutine jobs.
- Alamofire, URLSession, generated OpenAPI clients -> existing Android networking layer, usually Ktor or Retrofit plus DTO serializers.
- Keychain -> EncryptedSharedPreferences or AndroidX Security encrypted storage.
- UserDefaults -> DataStore.
- CoreData/SQLite caches -> Room.
- APNs and notification settings -> FCM plus Android notification channels.
- HealthKit, location, camera, photo picker, document picker -> Android permission-gated equivalents.

## References

Read `references/android-porting-checklist.md` when starting a new Android port or when auditing completeness before delivery.
