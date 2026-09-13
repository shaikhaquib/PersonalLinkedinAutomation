# Android Architecture & Modularization Knowledge Base

## Clean Architecture & Unidirectional Data Flow (UDF)
- Layer separation:
  - `UI Layer`: Composables + ViewModels + UI State / UI Events. UI should be passive and render states deterministically.
  - `Domain Layer` (Optional but useful for complex business logic): Pure Kotlin UseCases. Single responsibility (`operator fun invoke(...)`). No Android SDK imports.
  - `Data Layer`: Repositories and DataSources (Local Room DB, Remote Retrofit/Ktor API, DataStore).
- Multi-Module Architecture:
  - Feature modularization vs layer modularization: Favor feature-by-feature modules (`:feature:auth`, `:feature:dashboard`, `:core:network`, `:core:database`, `:core:designsystem`, `:core:model`).
  - Build times: Modularization enables Gradle parallel build execution, incremental compilation, and compilation caching.
  - Dependency inversion: Higher-level modules depend on abstractions (interfaces in API modules), not implementation details.
- State Modeling:
  - Model UI state as sealed interfaces: `UiState.Loading`, `UiState.Success`, `UiState.Error`.
  - Prefer immutable data structures.
  - Avoid separate boolean flags (`isLoading`, `isError`, `isSuccess`) that create invalid intermediate states.
