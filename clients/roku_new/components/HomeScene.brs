sub init()
    m.topNav = m.top.findNode("topNav")
    m.btnHome = m.top.findNode("btnHome")
    m.btnMovies = m.top.findNode("btnMovies")
    m.btnTV = m.top.findNode("btnTV")
    m.btnSettings = m.top.findNode("btnSettings")
    
    m.homeRowList = m.top.findNode("homeRowList")
    
    m.tabMovies = m.top.findNode("tabMovies")
    m.tabTV = m.top.findNode("tabTV")
    
    m.allMoviesGrid = m.top.findNode("allMoviesGrid")
    m.allTvGrid = m.top.findNode("allTvGrid")
    
    ' Sort Buttons
    m.btnMoviesSort = m.top.findNode("btnMoviesSort")
    m.btnTvSort = m.top.findNode("btnTvSort")
    
    m.loadingLabel = m.top.findNode("loadingLabel")
    
    m.heroBackdrop = m.top.findNode("heroBackdrop")
    m.heroTitle = m.top.findNode("heroTitle")
    m.heroOverview = m.top.findNode("heroOverview")
    
    m.top.observeField("visible", "OnVisibleChange")
    
    ' Button Observers
    m.btnHome.observeField("buttonSelected", "OnHomeInfo")
    m.btnMovies.observeField("buttonSelected", "OnMoviesInfo")
    m.btnTV.observeField("buttonSelected", "OnTVInfo")
    m.btnSettings.observeField("buttonSelected", "OnSettingsSelected")
    
    m.btnMoviesSort.observeField("buttonSelected", "OnMoviesSort")
    m.btnTvSort.observeField("buttonSelected", "OnTvSort")
    
    ' Default Sort Modes
    m.movieSortMode = "recent"
    m.tvSortMode = "recent"
    
    m.top.observeField("server_url", "OnFieldsReady")
    m.top.observeField("auth_token", "OnFieldsReady")
    
    ' Observer RowList Focus
    m.homeRowList.observeField("rowItemSelected", "OnRowItemSelected")
    m.homeRowList.observeField("rowItemFocused", "OnRowItemFocused")
    
    m.lastMovieIdx = 0
    m.lastTvIdx = 0
    
    ' Observe Grids
    grids = [m.allMoviesGrid, m.allTvGrid]
    for each g in grids
        if g <> invalid
            g.observeField("itemSelected", "OnItemSelected")
            g.observeField("itemFocused", "OnItemFocused")
        end if
    end for
    
    
    CheckReady()
end sub

sub OnHomeInfo()
    SwitchTab(0)
end sub

sub OnMoviesInfo()
    SwitchTab(1)
end sub

sub OnTVInfo()
    SwitchTab(2)
end sub

sub OnMoviesSort()
    if m.movieSortMode = "recent"
        m.movieSortMode = "alpha"
        m.btnMoviesSort.text = "Sort: A-Z"
    else if m.movieSortMode = "alpha"
        m.movieSortMode = "year"
        m.btnMoviesSort.text = "Sort: Year"
    else
        m.movieSortMode = "recent"
        m.btnMoviesSort.text = "Sort: Recent"
    end if
    FetchMovies()
end sub

sub OnTvSort()
    if m.tvSortMode = "recent"
        m.tvSortMode = "alpha"
        m.btnTvSort.text = "Sort: A-Z"
    else if m.tvSortMode = "alpha"
        m.tvSortMode = "year"
        m.btnTvSort.text = "Sort: Year"
    else
        m.tvSortMode = "recent"
        m.btnTvSort.text = "Sort: Recent"
    end if
    FetchTvShows()
end sub

sub SwitchTab(idx)
    m.homeRowList.visible = (idx = 0)
    m.tabMovies.visible = (idx = 1)
    m.tabTV.visible = (idx = 2)
    
    if idx = 1
        if m.allMoviesGrid.content = invalid or m.allMoviesGrid.content.getChildCount() = 0
            FetchMovies()
        else
            ' m.allMoviesGrid.setFocus(true) ' Don't auto-focus grid on click, stay on button
        end if
    else if idx = 2
        if m.allTvGrid.content = invalid or m.allTvGrid.content.getChildCount() = 0
            FetchTvShows()
        else
            ' m.allTvGrid.setFocus(true)
        end if
    else if idx = 0
        ' m.homeRowList.setFocus(true)
    end if
end sub

sub OnSettingsSelected()
    LaunchSettings()
end sub

sub OnRowItemFocused(event)
    ' RowList focus: [rowIndex, itemIndex]
    idx = event.getData()
    rowIndex = idx[0]
    itemIndex = idx[1]
    
    row = m.homeRowList.content.getChild(rowIndex)
    if row <> invalid
        item = row.getChild(itemIndex)
        if item <> invalid then UpdateHero(item)
    end if
end sub

sub OnRowItemSelected(event)
    idx = event.getData()
    row = m.homeRowList.content.getChild(idx[0])
    item = row.getChild(idx[1])
    HandleSelection(item)
end sub

sub OnItemSelected(event)
    ' Standard Grid Selection
    grid = event.getRoSGNode()
    idx = event.getData()
    item = grid.content.getChild(idx)
    HandleSelection(item)
end sub

sub OnItemFocused(event)
    ' Standard Grid Focus
    grid = event.getRoSGNode()
    if grid.content = invalid return
    if m.isNavigating = true return ' Prevent loops
    idx = event.getData()
    numCols = 7
    
    ' Infinite Scroll / Wrap Detection
    ' PosterGrid often consumes onKeyEvent, bypassing manual blocks.
    ' So we detect the wrap AFTER it happens and bounce it back.
    
    ' Detect Wrap DOWN (Bottom -> Top)
    if grid.id = "allMoviesGrid"
        ' Movies Watchdog
        if m.lastMovieIdx <> invalid
             count = grid.content.getChildCount()
             numCols = 7
             
             prevRow = Int(m.lastMovieIdx / numCols)
             currRow = Int(idx / numCols)
             lastRow = Int((count - 1) / numCols)
             
             ' Wrap Down (Bottom -> Top)
             if prevRow = lastRow and currRow = 0
                 print " [WATCHDOG] Wrap Down (Loop) Detected. Bouncing Back."
                 grid.jumpToItem = m.lastMovieIdx
                 return
             end if
             
             ' Wrap Up (Top -> Bottom)
             ' This means user pressed UP at the top. Escape to Top Nav.
             if prevRow = 0 and currRow = lastRow
                 print " [WATCHDOG] Wrap Up (Escape) Detected. Moving to Top Nav."
                 if m.tabMovies.visible then m.btnMovies.setFocus(true)
                 if m.tabTV.visible then m.btnTV.setFocus(true)
                 ' Reset grid focus to top so when they come back, they are at top
                 grid.jumpToItem = 0
                 return
             end if
        end if
        m.lastMovieIdx = idx
        
    else if grid.id = "allTvGrid"
        ' TV Watchdog
        if m.lastTvIdx <> invalid
             count = grid.content.getChildCount()
             numCols = 7
             
             prevRow = Int(m.lastTvIdx / numCols)
             currRow = Int(idx / numCols)
             lastRow = Int((count - 1) / numCols)
             
             if prevRow = lastRow and currRow = 0
                 print " [WATCHDOG] Wrap Down (Loop) Detected. Bouncing Back."
                 grid.jumpToItem = m.lastTvIdx
                 return
             end if
             
             if prevRow = 0 and currRow = lastRow
                 print " [WATCHDOG] Wrap Up (Escape) Detected. Moving to Top Nav."
                 if m.tabMovies.visible then m.btnMovies.setFocus(true)
                 if m.tabTV.visible then m.btnTV.setFocus(true)
                 grid.jumpToItem = 0
                 return
             end if
        end if
        m.lastTvIdx = idx
    end if
    
    item = grid.content.getChild(idx)
    if item <> invalid then UpdateHero(item)
end sub

sub HandleSelection(item)
    if item = invalid return
    id = item.id
    kind = ""
    if item.hasField("itemKind") then kind = item.itemKind
    
    print "Selected: " + item.title + " Kind: " + kind
    
    if kind = "movie"
        LaunchMovieDetails(id)
    else if kind = "show" or kind = "series"
        LaunchShowDetails(id)
    else
        print "Unknown kind"
    end if
end sub


sub UpdateHero(item)
    if m.heroTitle <> invalid then m.heroTitle.text = item.title
    if m.heroOverview <> invalid then m.heroOverview.text = item.description
    
    if m.heroBackdrop <> invalid
        if item.hasField("backdropUrl") and item.backdropUrl <> ""
            m.heroBackdrop.uri = item.backdropUrl
        else
            m.heroBackdrop.uri = item.hdposterurl 
        end if
    end if
end sub

sub OnFieldsReady()
    CheckReady()
end sub

sub CheckReady()
    if m.top.server_url <> "" and m.top.auth_token <> ""
        if m.fetch_started = invalid
             m.fetch_started = true
             FetchDashboard()
        end if
    end if
end sub

sub OnVisibleChange()
    if m.top.visible = true and m.detailsOpen <> true
        FocusTopNav()
    end if
end sub

' ================= CONTENT HELPERS =================

sub FetchDashboard()
    if m.top.server_url = "" return
    
    task = CreateObject("roSGNode", "NetworkTask")
    task.url = m.top.server_url + "/api/dashboard/"
    task.headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.observeField("response", "OnDashboardResponse")
    task.control = "RUN"
end sub

sub OnDashboardResponse(event)
    response = event.getData()
    m.loadingLabel.visible = false
    
    if response = invalid or response.status = "error" 
         print "Error fetching dashboard"
         return
    end if
    
    rootContent = CreateObject("roSGNode", "ContentNode")
    
    ' Continue Watching Row
    if response.continue_watching <> invalid and response.continue_watching.Count() > 0
        row = CreateObject("roSGNode", "ContentNode")
        row.title = "Continue Watching"
        for each item in response.continue_watching
            node = CreateContentNode(item)
            if item.kind <> invalid then node.itemKind = item.kind else node.itemKind = ""
            row.appendChild(node)
        end for
        rootContent.appendChild(row)
    end if
    
    ' Movies Row
    if response.recent_movies <> invalid and response.recent_movies.Count() > 0
        row = CreateObject("roSGNode", "ContentNode")
        row.title = "Recently Added Movies"
        for each item in response.recent_movies
            node = CreateContentNode(item)
            node.itemKind = "movie"
            row.appendChild(node)
        end for
        rootContent.appendChild(row)
    end if

    ' TV Row
    if response.recent_tv <> invalid and response.recent_tv.Count() > 0
        row = CreateObject("roSGNode", "ContentNode")
        row.title = "Recently Added TV"
        for each item in response.recent_tv
            node = CreateContentNode(item)
            node.itemKind = "show"
            row.appendChild(node)
        end for
        rootContent.appendChild(row)
    end if
    
    m.homeRowList.content = rootContent
    FocusTopNav()
end sub

sub FetchMovies()
    m.loadingLabel.visible = true
    task = CreateObject("roSGNode", "NetworkTask")
    task.url = m.top.server_url + "/api/movies?page=1&page_size=60&sort=" + m.movieSortMode
    task.headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.observeField("response", "OnMoviesResponse")
    task.control = "RUN"
end sub

sub OnMoviesResponse(event)
    m.loadingLabel.visible = false
    response = event.getData()
    if response = invalid or response.items = invalid return
    
    content = CreateObject("roSGNode", "ContentNode")
    for each item in response.items
        node = CreateContentNode(item)
        node.itemKind = "movie"
        content.appendChild(node)
    end for
    content = CreateObject("roSGNode", "ContentNode")
    for each item in response.items
        node = CreateContentNode(item)
        node.itemKind = "movie"
        content.appendChild(node)
    end for
    m.allMoviesGrid.content = content
end sub

sub FetchTvShows()
    m.loadingLabel.visible = true
    task = CreateObject("roSGNode", "NetworkTask")
    task.url = m.top.server_url + "/api/tv?page=1&page_size=60&sort=" + m.tvSortMode
    task.headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.observeField("response", "OnTvShowsResponse")
    task.control = "RUN"
end sub

sub OnTvShowsResponse(event)
    m.loadingLabel.visible = false
    response = event.getData()
    if response = invalid or response.items = invalid return
    
    content = CreateObject("roSGNode", "ContentNode")
    for each item in response.items
        node = CreateContentNode(item)
        node.itemKind = "show"
        content.appendChild(node)
    end for
    m.allTvGrid.content = content
end sub

function CreateContentNode(item as Object) as Object
    node = CreateObject("roSGNode", "ContentNode")
    
    title = "Untitled"
    if item.title <> invalid then title = item.title
    
    node.title = title
    if item.id <> invalid then node.id = item.id else node.id = ""
    
    node.hdposterurl = BuildPosterUrl(item)
    node.shortdescriptionline1 = title
    node.description = iif(item.overview <> invalid, item.overview, "")
    
    node.addField("backdropUrl", "string", false)
    backdrop = ""
    if item.backdrop_url <> invalid and item.backdrop_url <> ""
        if Left(item.backdrop_url, 4) = "http"
             backdrop = item.backdrop_url
        else
             backdrop = m.top.server_url + item.backdrop_url
        end if
    end if
    node.backdropUrl = backdrop
    
    node.addField("itemKind", "string", false)
    
    return node
end function

function BuildPosterUrl(item as Object) as String
    if item = invalid return "pkg:/images/placeholder.png"
    poster = ""
    if item.poster_url <> invalid and item.poster_url <> ""
        poster = item.poster_url
    else if item.extra_json <> invalid and item.extra_json.poster <> invalid
        poster = item.extra_json.poster
    end if
    
    if poster <> ""
        if Left(poster, 4) = "http" then return poster
        return m.top.server_url + poster
    end if
    return "pkg:/images/placeholder.png"
end function

sub LaunchMovieDetails(movieId as String)
    if movieId = "" or movieId = invalid return
    if m.detailsOpen = true return
    
    scene = CreateObject("roSGNode", "MovieDetailsScene")
    scene.movie_id = movieId
    scene.server_url = m.top.server_url
    scene.auth_token = m.top.auth_token
    
    m.top.appendChild(scene)
    scene.setFocus(true)
    m.detailsOpen = true
    scene.observeField("wasClosed", "OnDetailsClosed")
end sub

sub LaunchShowDetails(showId as String)
    if showId = "" or showId = invalid return
    if m.detailsOpen = true return
    
    scene = CreateObject("roSGNode", "ShowDetailsScene")
    scene.show_id = showId
    scene.server_url = m.top.server_url
    scene.auth_token = m.top.auth_token
    
    m.top.appendChild(scene)
    scene.setFocus(true)
    m.detailsOpen = true
    scene.observeField("wasClosed", "OnDetailsClosed")
end sub

sub LaunchSettings()
    if m.detailsOpen = true return
    scene = CreateObject("roSGNode", "SettingsScene")
    scene.server_url = m.top.server_url
    scene.auth_token = m.top.auth_token
    
    m.top.appendChild(scene)
    scene.setFocus(true)
    m.detailsOpen = true
    
    m.settingsScene = scene
    scene.observeField("wasClosed", "OnSettingsClosed")
end sub

sub OnSettingsClosed()
    m.detailsOpen = false
    
    if m.settingsScene.logout_triggered = true
        print "Logout triggered"
        m.top.logout_requested = true
    else
        m.top.removeChild(m.settingsScene) ' Remove from view
        FocusTopNav()
    end if
    m.settingsScene = invalid
end sub

sub OnDetailsClosed()
    m.detailsOpen = false
    ' Restore focus
    FocusTopNav() 
end sub


function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    print "HomeScene Received Key: " + key
    
    if key = "back"
        ' If in Movie/TV tab, go back to Home
        if not m.homeRowList.visible
            SwitchTab(0)
            m.btnHome.setFocus(true)
            return true
        end if
        return false
    end if
    
    ' TopNav Navigation Logic
    if m.topNav.isInFocusChain()
        if key = "right"
            if m.btnHome.hasFocus() 
                m.btnMovies.setFocus(true)
            else if m.btnMovies.hasFocus() 
                m.btnTV.setFocus(true)
            else if m.btnTV.hasFocus() 
                m.btnSettings.setFocus(true)
            end if
            return true
        else if key = "left"
            if m.btnMovies.hasFocus() 
                m.btnHome.setFocus(true)
            else if m.btnTV.hasFocus() 
                m.btnMovies.setFocus(true)
            else if m.btnSettings.hasFocus() 
                m.btnTV.setFocus(true)
            end if
            return true
        else if key = "down"
            print "Handling DOWN from TopNav Buttons"
             if m.homeRowList.visible
                 m.homeRowList.setFocus(true)
             else if m.tabMovies.visible
                 ' Focus Sort Button if visible
                 m.btnMoviesSort.setFocus(true)
             else if m.tabTV.visible
                 ' Focus Sort Button
                 m.btnTvSort.setFocus(true)
             end if
             return true
        end if
    else if m.btnMoviesSort.hasFocus() or m.btnTvSort.hasFocus()
        ' From Sort Button
        if key = "down"
             if m.tabMovies.visible
                 m.allMoviesGrid.setFocus(true)
             else if m.tabTV.visible
                 m.allTvGrid.setFocus(true)
             end if
             return true
        else if key = "up"
             ' Back to Top Nav
             if m.tabMovies.visible
                 m.btnMovies.setFocus(true)
             else if m.tabTV.visible
                 m.btnTV.setFocus(true)
             end if
             return true
        end if
            ' Grid Key Handling delegated to Watchdog (Wrap Detection)
            return false
            
    else if key = "down"
            ' Delegated to Watchdog
            return false
    end if
    
    return false
end function

sub FocusTopNav()
    m.isNavigating = true ' Lock focus events
    if m.tabMovies.visible
        m.btnMovies.setFocus(true)
    else if m.tabTV.visible
        m.btnTV.setFocus(true)
    else if m.homeRowList.visible
        m.btnHome.setFocus(true)
    else
        m.btnHome.setFocus(true)
    end if
    m.isNavigating = false ' Unlock
end sub
