sub init()
  m.title = m.top.findNode("title")
  m.seasonsGrid = m.top.findNode("seasonsGrid")
  
  m.serverUrl = GetServerUrl()
  m.token = GetAuthToken()
  
  m.seasonsGrid.observeField("itemSelected", "OnSeasonSelected")
  
  ' Get data from navigation
  data = GetNavigationData()
  if data <> invalid then
    m.showId = data.showId
    m.showTitle = data.showTitle
    if m.title <> invalid and m.showTitle <> invalid then
      m.title.text = m.showTitle + " - Seasons"
    end if
    LoadSeasons()
  end if
  
  m.top.setFocus(true)
end sub

sub LoadSeasons()
  response = ApiGetSeasons(m.serverUrl, m.token, m.showId)
  if response = invalid then
    print "Failed to load seasons"
    return
  end if
  
  content = CreateObject("roSGNode", "ContentNode")
  
  for each season in response
    item = content.createChild("ContentNode")
    item.title = season.title
    if season.season <> invalid then
      item.title = "Season " + season.season.ToStr()
    end if
    item.id = season.id
    item.seasonNumber = season.season
    item.description = item.title
  end for
  
  m.seasonsGrid.content = content
end sub

sub OnSeasonSelected(event)
  selectedIndex = event.getData()
  if m.seasonsGrid.content <> invalid and m.seasonsGrid.content.getChildCount() > selectedIndex then
    season = m.seasonsGrid.content.getChild(selectedIndex)
    if season <> invalid then
      ' Navigate to episodes
      data = { showId: m.showId, seasonNumber: season.seasonNumber, seasonTitle: season.title }
      NavigateToScene("EpisodesScene", data)
    end if
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

