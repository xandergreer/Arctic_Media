sub init()
    m.backdrop = m.top.findNode("backdrop")
    m.poster = m.top.findNode("poster")
    m.title = m.top.findNode("title")
    m.metadata = m.top.findNode("metadata")
    m.overview = m.top.findNode("overview")
    m.seasonList = m.top.findNode("seasonList")
    m.loadingLabel = m.top.findNode("loadingLabel")
    
    m.top.observeField("show_id", "OnFieldsReady")
    m.top.observeField("server_url", "OnFieldsReady")
    m.top.observeField("auth_token", "OnFieldsReady")
    
    m.seasonList.observeField("itemSelected", "OnSeasonSelected")
    
    CheckReady()
end sub

sub CheckReady()
    if m.top.show_id <> "" and m.top.server_url <> "" and m.top.auth_token <> "" then
        if m.fetch_started = invalid then
             m.fetch_started = true
             FetchShowDetails()
        end if
    end if
end sub

sub OnFieldsReady()
    CheckReady()
end sub

sub FetchShowDetails()
    print "Fetching show details: " + m.top.show_id
    
    task = CreateObject("roSGNode", "NetworkTask")
    task.setField("url", m.top.server_url + "/api/show/" + m.top.show_id)
    task.setField("method", "GET")
    
    headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.setField("headers", headers) 
    task.observeField("response", "OnShowResponse")
    task.control = "RUN"
end sub

sub OnShowResponse(event)
    response = event.getData()
    m.loadingLabel.visible = false
    
    if response = invalid or response.status = "error"
        print "Show fetch error"
        msg = "Error loading show details"
        if response <> invalid and response.message <> invalid then msg = response.message
        
        m.loadingLabel.text = msg
        m.loadingLabel.visible = true
        m.loadingLabel.color = "#FF0000"
        return
    end if
    
    ' Set Title
    if response.title <> invalid
        m.title.text = response.title
    else
        m.title.text = "Unknown Title"
    end if
    
    ' Set Metadata (Year)
    if response.year <> invalid and response.year <> 0
        m.metadata.text = response.year.ToStr()
    end if
    
    ' Set Overview
    overviewText = ""
    if response.overview <> invalid and response.overview <> ""
        overviewText = response.overview
    end if
    if overviewText = "" then overviewText = "No description available."
    m.overview.text = overviewText
    
    ' Set Poster
    if response.poster_url <> invalid and response.poster_url <> ""
        posterUri = ""
        if Left(response.poster_url, 4) = "http"
            posterUri = response.poster_url
        else
            posterUri = m.top.server_url + response.poster_url
        end if
        m.poster.uri = posterUri
    end if
    
    ' Set Backdrop
    if response.backdrop_url <> invalid and response.backdrop_url <> ""
        backdropUri = ""
        if Left(response.backdrop_url, 4) = "http"
            backdropUri = response.backdrop_url
        else
            backdropUri = m.top.server_url + response.backdrop_url
        end if
        m.backdrop.uri = backdropUri
        m.backdropUri = backdropUri
    end if
    
    ' Populate Seasons
    if response.seasons <> invalid and response.seasons.Count() > 0 then
        populateSeasonList(response.seasons)
    else
        ' No seasons?
        content = CreateObject("roSGNode", "ContentNode")
        item = content.createChild("ContentNode")
        item.title = "No Seasons Found"
        m.seasonList.content = content
    end if
    
    m.seasonList.setFocus(true)
end sub

sub populateSeasonList(seasons as Object)
    content = CreateObject("roSGNode", "ContentNode")
    
    for each s in seasons
        item = content.createChild("ContentNode")
        item.title = s.title
        item.shortdescriptionline1 = s.title
        item.id = s.id
        
        poster = "pkg:/images/placeholder.png"
        if s.poster_url <> invalid and s.poster_url <> ""
            if Left(s.poster_url, 4) = "http"
                 poster = s.poster_url
            else
                 poster = m.top.server_url + s.poster_url
            end if
        else if m.poster.uri <> invalid and m.poster.uri <> "" 
             poster = m.poster.uri
        end if
        item.hdposterurl = poster
    end for
    
    m.seasonList.content = content
end sub

sub OnSeasonSelected()
    idx = m.seasonList.itemSelected
    content = m.seasonList.content
    if content <> invalid then
        item = content.getChild(idx)
        if item <> invalid then
            print "Selected Season: " + item.title + " ID: " + item.id
            LaunchSeasonDetails(item.id, item.title)
        end if
    end if
end sub

sub LaunchSeasonDetails(seasonId as String, seasonTitle as String)
    print "Launching Season Details: " + seasonTitle + " (" + seasonId + ")"
    
    scene = CreateObject("roSGNode", "SeasonDetailsScene")
    scene.show_id = m.top.show_id
    scene.season_title = seasonTitle
    scene.server_url = m.top.server_url
    scene.auth_token = m.top.auth_token
    scene.backdrop_url = m.backdropUri
    scene.season_id = seasonId ' Set this LAST to trigger FetchEpisodes robustly
    
    m.top.appendChild(scene)
    scene.setFocus(true)
    scene.observeField("wasClosed", "OnSeasonClosed")
end sub

sub OnSeasonClosed()
    m.seasonList.setFocus(true)
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    
    if key = "back"
        ' Remove this details view and return to grid
        parent = m.top.getParent()
        if parent <> invalid
            m.top.wasClosed = true
            parent.removeChild(m.top)
        end if
        return true
    end if
    
    return false
end function
