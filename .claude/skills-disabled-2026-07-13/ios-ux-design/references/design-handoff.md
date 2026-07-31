# Design Handoff Specifications

When creating specs for developers, include:

## Layout Specifications
- Point measurements (not pixels)
- Safe area considerations
- Size class adaptations
- Minimum touch targets verified

## Typography
- Text style names (not sizes)
- Color names (semantic)
- Line height: Auto (system default)
- Alignment specifications

## Colors
- Semantic color names (e.g., .label, .systemBlue)
- Custom color asset names if needed
- All 4 variants defined for custom colors

## Icons
- SF Symbol names and configurations
- Weight and scale specifications
- Rendering mode (monochrome, hierarchical, palette, multicolor)
- No custom PNGs unless truly necessary

## Interactions
- Gesture specifications
- Haptic feedback points
- Animation descriptions (system animations preferred)
- Loading and error states

## Accessibility
- VoiceOver labels and hints
- Text style usage (for Dynamic Type)
- Alternative text for images
- Keyboard navigation order

## Screen Size Adaptation

### Size Classes
- Compact width: iPhone portrait, iPhone landscape (smaller models)
- Regular width: iPad portrait/landscape, iPhone landscape (larger models)
- Adapt layouts based on horizontal size class
- Use SwiftUI's horizontalSizeClass environment value

### Safe Area Handling
- Always respect safe area insets
- Use .safeAreaInset modifier for custom overlays
- Account for notch, Dynamic Island, home indicator
- Navigation bar and tab bar auto-handle safe areas

### iPad Considerations
- Larger tap targets acceptable (but 44pt still minimum)
- Multi-column layouts (UISplitViewController)
- Popovers instead of action sheets
- Keyboard shortcuts (iPad with keyboard)
- Drag and drop between apps

## iOS 26+ Liquid Glass Considerations

### New Visual Language
- Translucent UI elements with glass-like properties
- Dynamic response to light, content, and motion
- Refined color palette (avoid vibrant primaries)
- Bolder typography with improved hierarchy
- Left-aligned text for better scannability

### Component Updates
- Navigation items with enhanced depth
- Sidebar with improved density
- Tab bar with search tab option
- Enhanced context menus
- Updated button styles with glass effects

### Migration Strategy
- Update to iOS 26 SDK
- Review component usage against new HIG
- Test appearance with Liquid Glass materials
- Update custom components to match system aesthetics
- Verify contrast ratios with new translucency
