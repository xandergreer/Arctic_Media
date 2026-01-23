sub init()
    m.title = m.top.findNode("title")
    m.episodeGrid = m.top.findNode("episodeGrid")
    m.loadingLabel = m.top.findNode("loadingLabel")
    m.backdrop = m.top.findNode("backdrop")
    
    m.top.observeField("show_id", "OnFieldsReady")
    m.top.observeField("season_id", "OnFieldsReady")
    m.top.observeField("server_url", "OnFieldsReady")
    m.top.observeField("auth_token", "OnFieldsReady")
    
    m.episodeGrid.observeField("itemSelected", "OnEpisodeSelected")
    
    CheckReady()
end sub

sub CheckReady()
    if m.top.season_id <> "" and m.top.server_url <> "" and m.top.auth_token <> "" then
        if m.fetch_started = invalid then
             m.fetch_started = true
             FetchEpisodes()
        end if
    end if
end sub

sub OnFieldsReady()
    CheckReady()
end sub

sub FetchEpisodes()
    if m.top.season_id = invalid or m.top.season_id = "" then return
    
    seasonTitle = "Episodes"
    if m.top.season_title <> "" then seasonTitle = m.top.season_title
    m.title.text = seasonTitle
    
    if m.top.backdrop_url <> "" then m.backdrop.uri = m.top.backdrop_url
    
    print "Fetching episodes for Season ID: " + m.top.season_id
    
    task = CreateObject("roSGNode", "NetworkTask")
    ' Use robust ID-based endpoint
    task.setField("url", m.top.server_url + "/api/season/" + m.top.season_id)
    task.setField("method", "GET")
    
    headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.setField("headers", headers) 
    task.observeField("response", "OnEpisodesResponse")
    task.control = "RUN"
end sub

sub OnEpisodesResponse(event)
    response = event.getData()
    m.loadingLabel.visible = false
    
    if response = invalid or (response.status <> invalid and response.status = "error") then
        m.loadingLabel.text = "Error loading episodes"
        m.loadingLabel.visible = true
        return
    end if
    
    items = []
    if response.episodes <> invalid
         items = response.episodes
    else if response.is_array = true
         items = response.data
    end if
    
    if items.Count() = 0 then
         m.loadingLabel.text = "No Episodes Found"
         m.loadingLabel.visible = true
    end if
    
    content = CreateObject("roSGNode", "ContentNode")
    for each ep in items
        node = content.createChild("ContentNode")
        
        epNum = ""
        if ep.episode <> invalid
             epNum = ep.episode.ToStr() + ". "
        end if
        
        epTitle = "Unknown Episode"
        if ep.title <> invalid then epTitle = ep.title
        
        node.title = epNum + epTitle
        node.shortdescriptionline1 = node.title
        
        airDate = ""
        if ep.air_date <> invalid then airDate = ep.air_date
        node.shortdescriptionline2 = airDate
        
        epId = ""
        if ep.id <> invalid then epId = ep.id
        node.id = epId
        
        overview = ""
        if ep.overview <> invalid then overview = ep.overview
        node.description = overview
        
        poster = "pkg:/images/placeholder.png"
        if ep.still <> invalid and ep.still <> ""
            if Left(ep.still, 4) = "http"
                 poster = ep.still
            else
                 poster = m.top.server_url + ep.still
            end if
        else if ep.poster_url <> invalid and ep.poster_url <> ""
            if Left(ep.poster_url, 4) = "http"
                 poster = ep.poster_url
            else
                 poster = m.top.server_url + ep.poster_url
            end if
        end if
        
        ' Set both SD and HD just in case
        node.hdPosterUrl = poster
        node.sdPosterUrl = poster
        
        ' DEBUG: Print the resolved URL
        if poster <> "pkg:/images/placeholder.png"
             print "EPISODE THUMB: " + poster
        end if
        
        ' Store first file ID if available for playback
        epFiles = ep.files
        if epFiles <> invalid and epFiles.Count() > 0
             node.addField("fileId", "string", false)
             node.fileId = epFiles[0].id
        else if ep.first_file_id <> invalid
             node.addField("fileId", "string", false)
             node.fileId = ep.first_file_id
        end if
    end for
    
    m.episodeGrid.content = content
    m.episodeGrid.setFocus(true)
end sub

sub OnEpisodeSelected()
    idx = m.episodeGrid.itemSelected
    content = m.episodeGrid.content
    if content <> invalid then
        item = content.getChild(idx)
        if item <> invalid then
             PlayEpisode(item)
        end if
    end if
end sub

sub PlayEpisode(item as Object)
    if item.fileId = invalid or item.fileId = "" then
        print "No file ID for episode"
        return
    end if
    
    print "Playing Episode: " + item.title + " File: " + item.fileId
    
    m.videoPlayer = m.top.findNode("videoPlayer")
    
    ' Prepare content
    content = CreateObject("roSGNode", "ContentNode")
    streamUrl = m.top.server_url + "/stream/" + item.fileId + "/master.m3u8"
    
    content.url = streamUrl
    content.streamFormat = "hls"
    content.title = item.title
    content.HttpSendClientCertificates = true
    content.HttpHeaders = [ "Authorization: Bearer " + m.top.auth_token ]
    
    m.videoPlayer.content = content
    m.videoPlayer.observeField("state", "OnVideoStateChange")
    
    ' Show and play
    m.videoPlayer.visible = true
    m.videoPlayer.enableUI = true
    m.videoPlayer.setFocus(true)
    m.videoPlayer.control = "play"
end sub

sub OnVideoStateChange()
    if m.videoPlayer = invalid return
    state = m.videoPlayer.state
    if state = "error" or state = "finished"
        m.videoPlayer.visible = false
        m.videoPlayer.control = "stop"
        m.episodeGrid.setFocus(true)
    end if
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    
    if m.videoPlayer <> invalid and m.videoPlayer.visible
        if key = "back"
            m.videoPlayer.control = "stop"
            m.videoPlayer.visible = false
            m.episodeGrid.setFocus(true)
            return true
        end if
        return false 
    end if
    
    if key = "back"
        parent = m.top.getParent()
        if parent <> invalid
            m.top.wasClosed = true
            parent.removeChild(m.top)
        end if
        return true
    end if
    
    return false
end function
