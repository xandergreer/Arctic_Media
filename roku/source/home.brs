sub init()
  m.moviesList = m.top.findNode("moviesList")
  m.showsList = m.top.findNode("showsList")
  
  m.serverUrl = GetServerUrl()
  m.token = GetAuthToken()
  
  ' Set up observers
  m.moviesList.observeField("itemSelected", "OnMovieSelected")
  m.showsList.observeField("itemSelected", "OnShowSelected")
  
  ' Set up key handler
  m.top.setFocus(true)
  m.top.observeField("focusedChild", "OnFocusChange")
  
  ' Load data
  LoadHomeContent()
end sub

sub OnFocusChange()
  if m.top.hasFocus() then
    if m.moviesList.content <> invalid and m.moviesList.content.getChildCount() > 0 then
      m.moviesList.setFocus(true)
    end if
  end if
end sub

sub LoadHomeContent()
  ' Load movies
  LoadMovies()
  ' Load TV shows
  LoadTVShows()
end sub

sub LoadMovies()
  response = ApiGetMovies(m.serverUrl, m.token, 1, 20)
  if response = invalid or response.items = invalid then
    print "Failed to load movies"
    return
  end if
  
  content = CreateObject("roSGNode", "ContentNode")
  rowContent = CreateObject("roSGNode", "ContentNode")
  rowContent.title = "Movies"
  
  for each movie in response.items
    item = rowContent.createChild("ContentNode")
    item.title = movie.title
    if movie.year <> invalid then
      item.title = item.title + " (" + movie.year.ToStr() + ")"
    end if
    
    ' Get poster URL
    posterUrl = ""
    if movie.extra_json <> invalid and movie.extra_json.poster <> invalid then
      posterUrl = GetPosterUrl(m.serverUrl, movie.extra_json.poster)
    else if movie.poster_url <> invalid then
      posterUrl = GetPosterUrl(m.serverUrl, movie.poster_url)
    end if
    item.hdPosterUrl = posterUrl
    item.sdPosterUrl = posterUrl
    item.id = movie.id
    item.description = movie.title
  end for
  
  content.appendChild(rowContent)
  m.moviesList.content = content
end sub

sub LoadTVShows()
  response = ApiGetTVShows(m.serverUrl, m.token, 1, 20)
  if response = invalid or response.items = invalid then
    print "Failed to load TV shows"
    return
  end if
  
  content = CreateObject("roSGNode", "ContentNode")
  rowContent = CreateObject("roSGNode", "ContentNode")
  rowContent.title = "TV Shows"
  
  for each show in response.items
    item = rowContent.createChild("ContentNode")
    item.title = show.title
    if show.year <> invalid then
      item.title = item.title + " (" + show.year.ToStr() + ")"
    end if
    
    ' Get poster URL
    posterUrl = ""
    if show.extra_json <> invalid and show.extra_json.poster <> invalid then
      posterUrl = GetPosterUrl(m.serverUrl, show.extra_json.poster)
    else if show.poster_url <> invalid then
      posterUrl = GetPosterUrl(m.serverUrl, show.poster_url)
    end if
    item.hdPosterUrl = posterUrl
    item.sdPosterUrl = posterUrl
    item.id = show.id
    item.description = show.title
  end for
  
  content.appendChild(rowContent)
  m.showsList.content = content
end sub

function onKeyEvent(key as string, press as boolean) as boolean
  if not press then return false
  
  if key = "down" then
    if m.moviesList.hasFocus() then
      m.showsList.setFocus(true)
      return true
    end if
  else if key = "up" then
    if m.showsList.hasFocus() then
      m.moviesList.setFocus(true)
      return true
    end if
  else if key = "back" then
    ' Exit app
    return false
  end if
  
  return false
end function

sub OnMovieSelected(event)
  selectedIndex = event.getData()
  row = m.moviesList.content.getChild(0)
  if row <> invalid and row.getChildCount() > selectedIndex[1] then
    movie = row.getChild(selectedIndex[1])
    if movie <> invalid then
      ' Navigate to movie detail/playback
      data = { type: "movie", id: movie.id, title: movie.title }
      NavigateToScene("MovieDetailScene", data)
    end if
  end if
end sub

sub OnShowSelected(event)
  selectedIndex = event.getData()
  row = m.showsList.content.getChild(0)
  if row <> invalid and row.getChildCount() > selectedIndex[1] then
    show = row.getChild(selectedIndex[1])
    if show <> invalid then
      ' Navigate to show detail
      data = { type: "show", id: show.id, title: show.title }
      NavigateToScene("ShowDetailScene", data)
    end if
  end if
end sub

