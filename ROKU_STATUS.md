# Roku App Status

## ✅ Completed
1. **Manifest** - App metadata configured
2. **Pairing Scene** - Full pairing flow with code display
3. **Authentication** - Bearer token support in API utilities
4. **Home Scene** - Basic structure with RowList for Movies/TV Shows
5. **Token Storage** - Persistent auth using roRegistrySection
6. **Server URL Management** - Auto-detection and storage
7. **Main Entry** - Auto-routes to Pairing or Home based on auth status

## 📦 Package Structure
```
roku/
├── manifest                      ✅ App metadata
├── images/                       ✅ App icons (HD/SD)
│   ├── app_icon_hd.png
│   └── app_icon_sd.png
├── components/                   ✅ SceneGraph XML files
│   ├── PairingScene.xml          ✅ Pairing/authentication
│   ├── HomeScene.xml             ✅ Home screen with RowList
│   └── MovieItem.xml             ✅ Placeholder poster component
└── source/                       ✅ BrightScript code
    ├── main.brs                  ✅ Entry point with auth check
    ├── api.brs                   ✅ HTTP utilities + Bearer auth
    ├── pairing.brs               ✅ Pairing flow logic
    └── home.brs                  ✅ Home content loading

build/
└── arctic-media.zip              ✅ Pre-built package
```

## 🎯 Current Functionality

### ✅ Working
- App launches and checks authentication state
- If not authenticated → PairingScene
- If authenticated → HomeScene
- Pairing flow requests code from server
- Code polling with auto-retry
- Token storage in registry
- Server URL detection and storage
- HomeScene loads Movies and TV Shows rows
- RowList displays poster grid
- Bearer token auth on all API calls

### ⏳ In Progress
- Navigation from pairing to home (manual restart required)
- Item selection handling
- Details screens

### 📝 TODO
- [ ] DetailsScene for movies/TV shows
- [ ] Seasons/Episodes navigation
- [ ] Video playback
- [ ] Better error handling
- [ ] Loading states
- [ ] Settings screen

## 🔧 How to Build & Deploy

### 1. Package the Channel
```bash
cd roku

# Create ZIP with proper structure
zip -r arctic-media.zip \
  manifest \
  images/ \
  components/ \
  source/
```

### 2. Deploy to Roku Device

**Option A: Roku Developer Dashboard**
1. Sign in at https://developer.roku.com
2. Go to "My Channels" → "Manage"
3. Upload `arctic-media.zip`
4. Add device IP for sideload

**Option B: Direct Sideload**
```bash
# Enable Developer Mode on Roku
# Settings → System → Developer Mode → Enable
# Note the IP address

# Install package
curl -F "mysubmit=Install" -F "archive=@arctic-media.zip" http://YOUR_ROKU_IP:8060/plugin_install
```

### 3. Test

**Pairing Flow:**
1. Launch app → Should show PairingScene
2. Enter code from server at `/pair`
3. Wait for authorization
4. App should show "Authorized!" message

**Home Screen:**
1. Close and restart app (auth cached)
2. Should load HomeScene
3. Shows two rows: Movies and TV Shows
4. Each row displays poster grid

**Debug:**
```bash
# Enable telnet debug on Roku
# Settings → System → Developer Mode → Enable

# Connect to debugger
telnet YOUR_ROKU_IP 8080

# View logs
telnet YOUR_ROKU_IP 8085
```

## 🐛 Known Issues

1. **No automatic scene switching** - User must restart app after pairing
   - Workaround: Currently shows success message, requires manual restart
   - Future: Implement proper scene switching or global state

2. **Missing video playback** - No VideoScene yet
   - Next: Create VideoScene with roVideoPlayer

3. **No details screens** - Can't view item details
   - Next: Create DetailsScene with poster, info, play button

4. **Limited error handling** - Failures not always surfaced to user
   - Next: Add error dialogs and retry logic

## 📈 Next Steps

1. **Complete HomeScene**
   - Fix item selection
   - Add navigation to details

2. **Create DetailsScene**
   - Show poster, title, overview
   - Add play button
   - For TV shows: show seasons

3. **Add Seasons/Episodes**
   - Create grid for seasons
   - Create grid for episodes
   - Navigate to video on play

4. **Video Playback**
   - Create VideoScene
   - Implement HLS streaming
   - Add playback controls

5. **Polish**
   - Add loading indicators
   - Improve error messages
   - Add settings screen
   - Optimize API calls

## 🔗 API Endpoints Used

- `POST /pair/request` - Get pairing code
- `POST /pair/poll` - Check pairing status  
- `GET /api/movies` - List movies (Bearer auth)
- `GET /api/tv` - List TV shows (Bearer auth)

All endpoints share the same backend as iOS app!

## 💡 Architecture Notes

**SceneGraph vs React Native:**
- Roku uses SceneGraph XML + BrightScript
- No reactive state like React
- Manual content node updates
- Focus management instead of navigation stack

**Storage:**
- Tokens → roRegistrySection (persistent)
- No AsyncStorage equivalent
- Can use roLocalStorage for larger data

**HTTP:**
- roUrlTransfer instead of axios
- Manual async handling
- No automatic retries (must implement)

**UI:**
- Absolute positioning (1920x1080)
- RowList for grids
- Poster for images
- Label for text
- No CSS or styling system

## ✨ Features Implemented

✅ Authentication via pairing code
✅ Server URL auto-detection
✅ Bearer token management
✅ TV shows grid
✅ Movies grid  
✅ Poster display
✅ Row-based navigation
✅ Error handling basics

This is a solid foundation! The core app structure works and can display content.
