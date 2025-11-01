# Roku Port - Migration Guide

## Overview
This guide explains how to port the React Native iOS app to Roku's BrightScript SceneGraph framework.

## ✅ What's Already Done

### 1. **Core Infrastructure**
- ✅ Manifest file created with proper metadata
- ✅ API utilities extended to support Bearer token authentication
- ✅ Pairing flow fully implemented
- ✅ Token storage using `roRegistrySection`

### 2. **API Compatibility**
The backend REST API is **fully compatible** between platforms:
- Same endpoints
- Same authentication (Bearer tokens)
- Same data structures
- Same response formats

## 🔄 Key Differences

### React Native → Roku Comparison

| Aspect | React Native (iOS) | Roku BrightScript |
|--------|-------------------|-------------------|
| **Language** | TypeScript/JavaScript | BrightScript (BASIC-like) |
| **UI Framework** | React + Native Components | SceneGraph (XML + BrightScript) |
| **State Management** | Zustand + AsyncStorage | Scene variables + roRegistrySection |
| **HTTP** | Axios | roUrlTransfer |
| **Navigation** | React Navigation Stack | Manual scene management |
| **Layout** | Flexbox | Absolute positioning/RowList |
| **Lists** | FlatList | RowList/MarkupList |
| **Images** | Image component | Poster component |
| **Video** | expo-video | Video node (roVideoPlayer) |

## 📝 What Needs to Be Ported

### 1. **HomeScreen → HomeScene**
```brightscript
' React Native: FlatList with numColumns
<FlatList numColumns={2} data={shows} renderItem={...} />

' Roku: Use RowList or MarkupList
rowList = m.top.findNode("contentGrid")
content = CreateObject("roSGNode", "ContentNode")
```

### 2. **Navigation Stack**
```brightscript
' React Native: navigation.navigate()
navigation.navigate('ShowDetail', { showId: show.id })

' Roku: Manual scene switching
m.top.setScene("DetailsScene", { showId: show.id })
```

### 3. **API Calls**
```brightscript
' React Native: axios
const response = await axios.get('/api/tv')

' Roku: HttpJson (already implemented)
json = HttpJson(url, "GET", invalid, true)
```

### 4. **State Persistence**
```brightscript
' React Native: AsyncStorage
await AsyncStorage.setItem('key', value)

' Roku: roRegistrySection
sec = CreateObject("roRegistrySection", "ArcticMedia")
sec.Write("key", value)
```

### 5. **Grid Density Selection**
```brightscript
' React Native: OptionsMenu component
<OptionsMenu density={density} onDensityChange={...} />

' Roku: Manual RowList.itemSize adjustment
' Adjust itemSize and spacing based on density preference
```

## 🎯 Implementation Priority

### Phase 1: Core Navigation ✅ (COMPLETED)
- ✅ Pairing flow
- ✅ Token storage
- ✅ API with Bearer auth

### Phase 2: Home Content (STARTED)
- ✅ Basic home scene structure
- ⏳ TV shows grid display
- ⏳ Movies grid display
- ⏳ Navigation between content types

### Phase 3: Details
- ⏳ Show detail screen
- ⏳ Movie detail screen
- ⏳ Episode detail screen
- ⏳ Season/episode grids

### Phase 4: Playback
- ⏳ Video playback scene
- ⏳ HLS streaming
- ⏳ Playback controls

### Phase 5: Polish
- ⏳ Settings screen
- ⏳ Grid density options
- ⏳ Search functionality
- ⏳ Loading states & error handling

## 📂 File Structure

```
roku/
├── manifest              # ✅ App metadata
├── images/              # ✅ App icons
├── components/          # SceneGraph XML files
│   ├── PairingScene.xml     # ✅ Pairing screen
│   ├── HomeScene.xml        # ✅ Started
│   ├── DetailsScene.xml     # ⏳ Todo
│   └── VideoScene.xml       # ⏳ Todo
└── source/              # BrightScript files
    ├── main.brs             # ✅ Entry point
    ├── api.brs              # ✅ HTTP utilities
    ├── pairing.brs          # ✅ Pairing logic
    ├── home.brs             # ✅ Started
    ├── details.brs          # ⏳ Todo
    └── playback.brs         # ⏳ Todo
```

## 🔧 How to Test

### 1. Package the Channel
```bash
cd roku
zip -r arctic-media.zip manifest images/ components/ source/
```

### 2. Load to Roku
- Enable Developer Mode on your Roku device
- Use Roku Developer Portal or sideload ZIP file
- Navigate to the channel and test pairing

### 3. Debug
```brightscript
' Add debug prints
print "Debug: Current state = " + m.currentState
```

Roku's debugger can be accessed via:
- Telnet to device IP on port 8080
- Use Roku Web Inspector
- View BrightScript console output

## 🎨 UI Layout Notes

Roku uses **absolute positioning** at 1920x1080 (FHD):
- Safe margins: 80px from edges
- Standard fonts: MediumSystemFont, LargeBoldSystemFont, etc.
- Common row heights: 60px, 100px, 200px
- Poster aspect ratio: 2:3 (typically 400x600)

## 🚀 Next Steps

1. Complete HomeScene with working grid display
2. Implement navigation to DetailsScene
3. Create DetailsScene for individual items
4. Add VideoScene for playback
5. Polish UI and add settings

## 📚 Resources

- [Roku Developer Documentation](https://developer.roku.com/docs)
- [SceneGraph XML Reference](https://developer.roku.com/docs/references/scenegraph/scenegraph-xml-elements.md)
- [BrightScript Language Reference](https://developer.roku.com/docs/references/brightscript/language/brightscript-language-reference.md)
- [Sample Channel Templates](https://github.com/rokudev/samples)

## 🤝 Porting Strategy

**Yes, you CAN port the iOS app to Roku!** The backend is identical, so focus on:
1. **UI layer only** - rebuild in SceneGraph
2. **API calls** - use existing HttpJson utilities
3. **State management** - use Scene variables instead of Zustand
4. **Navigation** - manual scene switching

The business logic, API structure, and data models translate directly!
