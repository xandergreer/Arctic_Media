sub init()
  m.poster = m.top.findNode("poster")
  m.title = m.top.findNode("title")
  m.year = m.top.findNode("year")
  m.description = m.top.findNode("description")
  m.playButton = m.top.findNode("playButton")
  
  m.serverUrl = GetServerUrl()
  m.token = GetAuthToken()
  
  m.playButton.observeField("buttonSelected", "OnPlayButton")
  m.top.observeField("itemId", "OnItemIdSet")
  
  ' Get data from navigation
  data = GetNavigationData()
  if data <> invalid then
    m.top.itemId = data.id
    m.top.itemType = data.type
  end if
  
  m.top.setFocus(true)
end sub

sub OnItemIdSet()
  if m.top.itemId = invalid or m.top.itemId = "" then return
  LoadItemDetails()
end sub

sub LoadItemDetails()
  itemId = m.top.itemId
  itemType = m.top.itemType
  
  if itemType = "movie" then
    ' Load movie details
    response = ApiGetMovies(m.serverUrl, m.token, 1, 1000)
    if response <> invalid and response.items <> invalid then
      for each movie in response.items
        if movie.id = itemId then
          DisplayMovieDetails(movie)
          return
        end if
      end for
    end if
  else if itemType = "show" then
    ' Load show details
    response = ApiGetTVShows(m.serverUrl, m.token, 1, 1000)
    if response <> invalid and response.items <> invalid then
      for each show in response.items
        if show.id = itemId then
          DisplayShowDetails(show)
          return
        end if
      end for
    end if
  end if
end sub

sub DisplayMovieDetails(movie)
  if m.title <> invalid then m.title.text = movie.title
  if m.year <> invalid and movie.year <> invalid then
    m.year.text = movie.year.ToStr()
  end if
  
  ' Get poster
  posterUrl = ""
  if movie.extra_json <> invalid and movie.extra_json.poster <> invalid then
    posterUrl = GetPosterUrl(m.serverUrl, movie.extra_json.poster)
  else if movie.poster_url <> invalid then
    posterUrl = GetPosterUrl(m.serverUrl, movie.poster_url)
  end if
  if posterUrl <> "" and m.poster <> invalid then
    m.poster.uri = posterUrl
  end if
  
  ' Description
  if movie.extra_json <> invalid and movie.extra_json.overview <> invalid then
    if m.description <> invalid then m.description.text = movie.extra_json.overview
  end if
end sub

sub DisplayShowDetails(show)
  if m.title <> invalid then m.title.text = show.title
  if m.year <> invalid and show.year <> invalid then
    m.year.text = show.year.ToStr()
  end if
  
  ' Get poster
  posterUrl = ""
  if show.extra_json <> invalid and show.extra_json.poster <> invalid then
    posterUrl = GetPosterUrl(m.serverUrl, show.extra_json.poster)
  else if show.poster_url <> invalid then
    posterUrl = GetPosterUrl(m.serverUrl, show.poster_url)
  end if
  if posterUrl <> "" and m.poster <> invalid then
    m.poster.uri = posterUrl
  end if
  
  ' Description
  if show.extra_json <> invalid and show.extra_json.overview <> invalid then
    if m.description <> invalid then m.description.text = show.extra_json.overview
  end if
  
  ' Change button text to "View Seasons"
  if m.playButton <> invalid then m.playButton.text = "View Seasons"
end sub

sub OnPlayButton()
  if m.top.itemType = "movie" then
    ' Play movie
    data = { itemId: m.top.itemId, itemType: "movie" }
    NavigateToScene("VideoScene", data)
  else if m.top.itemType = "show" then
    ' Navigate to seasons
    data = { showId: m.top.itemId, showTitle: m.title.text }
    NavigateToScene("SeasonsScene", data)
  end if
end sub

function onKeyEvent(key as string, press as boolean) as boolean
  if not press then return false
  
  if key = "back" then
    NavigateToScene("HomeScene", invalid)
    return true
  end if
  
  return false
end function

