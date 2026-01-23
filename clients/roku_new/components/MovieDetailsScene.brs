sub init()
    m.backdrop = m.top.findNode("backdrop")
    m.poster = m.top.findNode("poster")
    m.title = m.top.findNode("title")
    m.metadata = m.top.findNode("metadata")
    m.overview = m.top.findNode("overview")
    m.playButton = m.top.findNode("playButton")
    m.loadingLabel = m.top.findNode("loadingLabel")
    
    m.top.observeField("movie_id", "OnFieldsReady")
    m.top.observeField("server_url", "OnFieldsReady")
    m.top.observeField("auth_token", "OnFieldsReady")
    
    m.playButton.observeField("buttonSelected", "OnPlaySelected")
    
    CheckReady()
end sub

sub CheckReady()
    if m.top.movie_id <> "" and m.top.server_url <> "" and m.top.auth_token <> ""
        if m.fetch_started = invalid
             m.fetch_started = true
             FetchMovieDetails()
        end if
    end if
end sub

sub OnFieldsReady()
    CheckReady()
end sub

sub FetchMovieDetails()
    print "Fetching movie details: " + m.top.movie_id
    
    task = CreateObject("roSGNode", "NetworkTask")
    task.setField("url", m.top.server_url + "/api/movie/" + m.top.movie_id)
    task.setField("method", "GET")
    
    headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.setField("headers", headers) 
    task.observeField("response", "OnMovieResponse")
    task.control = "RUN"
end sub

sub OnMovieResponse(event)
    response = event.getData()
    m.loadingLabel.visible = false
    
    if response = invalid or response.status = "error"
        print "Movie fetch error"
        msg = "Error loading movie details"
        if response <> invalid and response.message <> invalid then msg = response.message
        
        m.loadingLabel.text = msg
        m.loadingLabel.visible = true
        m.loadingLabel.color = "#FF0000"
        return
    end if
    
    ' Store file ID for playback
    if response.files <> invalid and response.files.Count() > 0
        m.fileId = response.files[0].id
    end if
    
    ' Set Title
    if response.title <> invalid
        m.title.text = response.title
    else
        m.title.text = "Unknown Title"
    end if
    
    ' Set Metadata (Year / Runtime)
    metaText = ""
    if response.year <> invalid and response.year <> 0
        metaText = response.year.ToStr()
    end if
    if response.runtime_ms <> invalid and response.runtime_ms > 0
        minutes = Int(response.runtime_ms / 60000)
        if metaText <> "" then metaText = metaText + " • "
        metaText = metaText + minutes.ToStr() + " min"
    end if
    m.metadata.text = metaText
    
    ' Set Overview
    overviewText = ""
    if response.overview <> invalid and response.overview <> ""
        overviewText = response.overview
    end if
    
    ' Add Directors
    if response.directors <> invalid and response.directors.Count() > 0
        dirNames = ""
        for i = 0 to response.directors.Count() - 1
            if i > 0 then dirNames = dirNames + ", "
            dirNames = dirNames + response.directors[i]
        end for
        if overviewText <> "" then overviewText = overviewText + chr(10) + chr(10)
        overviewText = overviewText + "Director: " + dirNames
    end if

    ' Add Cast
    if response.cast <> invalid and response.cast.Count() > 0
        castNames = ""
        count = response.cast.Count()
        if count > 8 then count = 8 ' Limit cast display
        for i = 0 to count - 1
            if i > 0 then castNames = castNames + ", "
            castNames = castNames + response.cast[i].name
        end for
        if overviewText <> "" then overviewText = overviewText + chr(10) + chr(10)
        overviewText = overviewText + "Cast: " + castNames
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
    end if
    
    m.playButton.setFocus(true)
end sub

sub OnPlaySelected()
    if m.top.movie_id = invalid or m.top.movie_id = "" return
    
    print "Play button selected, Item ID: " + m.top.movie_id
    
    m.videoPlayer = m.top.findNode("videoPlayer")
    
    ' Prepare content
    content = CreateObject("roSGNode", "ContentNode")
    streamUrl = m.top.server_url + "/stream/" + m.top.movie_id + "/master.m3u8"
    print "Streaming URL: " + streamUrl
    
    content.url = streamUrl
    content.streamFormat = "hls"
    content.title = m.title.text
    content.HttpSendClientCertificates = true
    content.HttpHeaders = [ "Authorization: Bearer " + m.top.auth_token ]
    
    m.videoPlayer.content = content
    m.videoPlayer.observeField("state", "OnVideoStateChange")
    
    ' Show and play
    m.videoPlayer.visible = true
    m.videoPlayer.enableUI = true ' Enable native controls
    m.videoPlayer.setFocus(true)
    m.videoPlayer.control = "play"
end sub

sub OnVideoStateChange()
    if m.videoPlayer = invalid return
    state = m.videoPlayer.state
    print "Video State: " + state
    
    if state = "error" or state = "finished"
        m.videoPlayer.visible = false
        m.videoPlayer.control = "stop"
        m.playButton.setFocus(true)
    end if
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    
    if m.videoPlayer <> invalid and m.videoPlayer.visible
        if key = "back"
            m.videoPlayer.control = "stop"
            m.videoPlayer.visible = false
            m.playButton.setFocus(true)
            return true
        end if
        return false 
    end if
    
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
