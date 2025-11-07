sub init()
  m.title = m.top.findNode("title")
  m.episodesList = m.top.findNode("episodesList")
  
  m.serverUrl = GetServerUrl()
  m.token = GetAuthToken()
  
  m.episodesList.observeField("itemSelected", "OnEpisodeSelected")
  
  ' Get data from navigation
  data = GetNavigationData()
  if data <> invalid then
    m.showId = data.showId
    m.seasonNumber = data.seasonNumber
    m.seasonTitle = data.seasonTitle
    if m.title <> invalid and m.seasonTitle <> invalid then
      m.title.text = m.seasonTitle + " - Episodes"
    end if
    LoadEpisodes()
  end if
  
  m.top.setFocus(true)
end sub

sub LoadEpisodes()
  response = ApiGetEpisodes(m.serverUrl, m.token, m.showId, m.seasonNumber)
  if response = invalid then
    print "Failed to load episodes"
    return
  end if
  
  content = CreateObject("roSGNode", "ContentNode")
  rowContent = CreateObject("roSGNode", "ContentNode")
  rowContent.title = "Episodes"
  
  for each episode in response
    item = rowContent.createChild("ContentNode")
    item.title = episode.title
    if episode.episode <> invalid then
      item.title = "Episode " + episode.episode.ToStr() + ": " + item.title
    end if
    
    ' Get still image
    stillUrl = ""
    if episode.still <> invalid then
      stillUrl = GetPosterUrl(m.serverUrl, episode.still)
    end if
    item.hdPosterUrl = stillUrl
    item.sdPosterUrl = stillUrl
    
    item.id = episode.id
    item.description = episode.title
  end for
  
  content.appendChild(rowContent)
  m.episodesList.content = content
end sub

sub OnEpisodeSelected(event)
  selectedIndex = event.getData()
  row = m.episodesList.content.getChild(0)
  if row <> invalid and row.getChildCount() > selectedIndex[1] then
    episode = row.getChild(selectedIndex[1])
    if episode <> invalid then
      ' Play episode
      data = { itemId: episode.id, itemType: "episode" }
      NavigateToScene("VideoScene", data)
    end if
  end if
end sub

function onKeyEvent(key as string, press as boolean) as boolean
  if not press then return false
  
  if key = "back" then
    ' Navigate back to seasons
    data = { showId: m.showId, showTitle: "" }
    NavigateToScene("SeasonsScene", data)
    return true
  end if
  
  return false
end function

