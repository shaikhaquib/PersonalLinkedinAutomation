# Android Foldables vs iOS Windowing & Software Architecture

## Core Architectural Differentiators
- **Multi-Resume Lifecycle (Android 10+ / 12L)**:
  - In standard mobile systems (and iOS on iPhone), only a single window/app can be in the `RESUMED` lifecycle state at any time; touching a second window pauses or throttles the first.
  - Android native WindowManager supports **Multi-Resume**: multiple visible activities across split-screen and multi-window stay simultaneously in the `RESUMED` state. Videos do not pause, animations do not freeze, and sensor loops continue concurrently when interacting with an adjacent app.
- **Jetpack WindowManager & Posture Detection**:
  - The `androidx.window:window` library models physical hinge states through `FoldingFeature`.
  - Distinguishes between `Posture.HALF_OPENED` (Tabletop / Flex mode) and `Posture.FLAT`, exposing exact hinge bounding rects and occlusion modes (`OcclusionType.FULL` vs `NONE`).
  - Allows UI architectures to bifurcate into control panes (lower half) and presentation viewports (upper half) dynamically.
- **Jetpack Compose Adaptive Layouts**:
  - `androidx.compose.material3.adaptive`: Standardizes screen scaling using `WindowSizeClass` (Compact < 600dp, Medium 600-839dp, Expanded >= 840dp).
  - Canonical layouts like `ListDetailPaneScaffold` and `SupportingPaneScaffold` handle foldable transitions without Activity recreation or manual state bundling.
- **App Continuity & Insets**:
  - Preserving continuity when unfolding from outer cover screen (Compact) to inner display (Expanded) requires declaring `configChanges="screenSize|smallestScreenSize|screenLayout|orientation"`.
  - Decoupling view models from hardcoded `DisplayMetrics` and observing reactive `WindowInsets` prevents layout clipping and UI jumps.
- **iOS Architectural Limitations**:
  - iOS on iPhone has zero native concept of multi-windowing, split-screen multitasking, or multi-resume. Even on iPadOS, Stage Manager is a desktop-emulation overlay with strict background execution limits, lacking hardware hinge-aware APIs or true concurrent activity lifecycles.
