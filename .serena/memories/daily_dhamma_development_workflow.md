# Daily Dhamma Development Workflow

## Project Location
`/Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app`

## Build Commands

### Development Build (for testing on real device)
```bash
cd /Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app
eas build --profile development --platform ios
```
- Creates Ad Hoc build for registered devices
- Install via link on real iPhone
- Requires Metro server connection for development

### Start Metro Server
```bash
npx expo start --clear
```
- Real device: Scan QR code with iPhone camera (must be on same WiFi)
- Simulator: Press `i` (requires simulator build)

### Production Build + Submit to App Store
```bash
eas build --profile production --platform ios --auto-submit
```
- Builds and automatically submits to App Store Connect
- Version auto-increments

### Local Build (for simulator)
```bash
eas build --profile development --platform ios --local
```
- Requires sufficient disk space (~10GB free)
- If fails with "ENOSPC", clean caches first

## Testing Onboarding Repeatedly

### Method 1: Reset Onboarding Button (Recommended)
1. Open app → Settings
2. Scroll to DEVELOPER section
3. Tap "Reset Onboarding"
4. Press `r` in terminal to reload app

### Method 2: Delete App
1. Delete app from device/simulator
2. Reinstall and run

## Common Issues

### "No development build installed" on Simulator
- Simulator needs a local build
- Run: `eas build --profile development --platform ios --local`

### "No development server found" on Real Device
- Ensure iPhone and Mac are on same WiFi network
- Scan QR code from terminal with iPhone camera
- Check firewall settings

### Disk Space Issues (ENOSPC)
```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/*
rm -rf ~/Library/Caches/com.apple.dt.Xcode/*
rm -rf ~/Library/Developer/Xcode/Archives/*
df -h /  # Check available space
```

## EAS Profiles (eas.json)

| Profile | Purpose | Distribution |
|---------|---------|--------------|
| development | Testing with Metro server | internal (Ad Hoc) |
| preview | Testing without server | internal |
| production | App Store submission | store |

## App Configuration

- Bundle ID: `com.dailydhamma.app`
- Supports Tablet: `false` (iPhone only)
- Apple Team ID: `S5U8UH3JLJ`

## Important Notes

1. **TestFlight vs Development Build**
   - Cannot have both installed (same bundle ID)
   - Delete one before installing the other

2. **Real Device Testing**
   - Device must be registered in Apple Developer Portal
   - Provisioning profile includes registered devices only

3. **Expo Go vs Development Build**
   - Press `s` in terminal to switch to Expo Go mode
   - Development build supports native modules better
