sub init()
  print "HomeScene: init() called"
  
  ' Get content grid
  m.contentGrid = m.top.findNode("homeContent")
  if m.contentGrid = invalid then
    print "ERROR: Could not find homeContent node"
    return
  end if
  
  ' Set up RowList
  m.contentGrid.itemComponentName = "StandardRowContent"
  m.contentGrid.rowItemSize = [[400, 600]]
  m.contentGrid.rowItemSpacing = [[16, 0]]
  m.contentGrid.showRowLabel = [false, false]
  m.contentGrid.showRowCounter = [false, false]
  
  ' Focus management
  m.contentGrid.setFocus(true)
  m.contentGrid.observeField("itemSelected", "onItemSelected")
  
  ' Load home content
  LoadHomeContent()
end sub

sub LoadHomeContent()
  print "Loading home content..."
  
  ' Create content node for RowList
  homeContent = CreateObject("roSGNode", "ContentNode")
  
  ' Row 1: Recently Added Movies
  moviesRow = CreateObject("roSGNode", "ContentNode")
  moviesRow.title = "Recently Added Movies"
  
  ' Row 2: Recently Added TV Shows
  showsRow = CreateObject("roSGNode", "ContentNode")
  showsRow.title = "Recently Added TV Shows"
  
  ' Add rows
  homeContent.appendChild(moviesRow)
  homeContent.appendChild(showsRow)
  
  ' Set content
  m.contentGrid.content = homeContent
  
  ' Load data asynchronously
  LoadMoviesAsync()
  LoadTVShowsAsync()
end sub

sub LoadMoviesAsync()
  server_url = LoadServerUrl()
  if server_url = "" then
    print "No server URL configured"
    return
  end if
  
  ' Fetch movies on background thread
  port = CreateObject("roMessagePort")
  urlTransfer = CreateObject("roUrlTransfer")
  urlTransfer.SetUrl(server_url + "/api/movies?page=1&page_size=50")
  
  ' Add auth header
  tokens = LoadTokens()
  if tokens.access_token <> "" then
    urlTransfer.AddHeader("Authorization", "Bearer " + tokens.access_token)
  end if
  
  urlTransfer.AddHeader("Accept", "application/json")
  urlTransfer.setCertificatesFile("common:/certs/ca-bundle.crt")
  urlTransfer.InitClientCertificates()
  urlTransfer.SetPort(port)
  urlTransfer.AsyncGetToString()
  
  print "Requesting movies from: " + server_url
  
  ' Wait for response with timeout
  msg = wait(5000, port)
  if msg <> invalid and msg.GetResponseCode() = 200 then
    jsonStr = urlTransfer.GetString()
    parser = CreateObject("roJsonParser")
    json = parser.Parse(jsonStr)
    
    if json <> invalid and json.items <> invalid then
      print "Loaded " + json.items.Count().toStr() + " movies"
      DisplayMovies(json.items)
    else
      print "Failed to parse movies response"
    end if
  else
    print "Failed to load movies"
  end if
end sub

sub LoadTVShowsAsync()
  server_url = LoadServerUrl()
  if server_url = "" then
    print "No server URL configured"
    return
  end if
  
  ' Fetch TV shows on background thread
  port = CreateObject("roMessagePort")
  urlTransfer = CreateObject("roUrlTransfer")
  urlTransfer.SetUrl(server_url + "/api/tv?page=1&page_size=50")
  
  ' Add auth header
  tokens = LoadTokens()
  if tokens.access_token <> "" then
    urlTransfer.AddHeader("Authorization", "Bearer " + tokens.access_token)
  end if
  
  urlTransfer.AddHeader("Accept", "application/json")
  urlTransfer.setCertificatesFile("common:/certs/ca-bundle.crt")
  urlTransfer.InitClientCertificates()
  urlTransfer.SetPort(port)
  urlTransfer.AsyncGetToString()
  
  print "Requesting TV shows from: " + server_url
  
  ' Wait for response with timeout
  msg = wait(5000, port)
  if msg <> invalid and msg.GetResponseCode() = 200 then
    jsonStr = urlTransfer.GetString()
    parser = CreateObject("roJsonParser")
    json = parser.Parse(jsonStr)
    
    if json <> invalid and json.items <> invalid then
      print "Loaded " + json.items.Count().toStr() + " TV shows"
      DisplayTVShows(json.items)
    else
      print "Failed to parse TV shows response"
    end if
  else
    print "Failed to load TV shows"
  end if
end sub

sub DisplayMovies(movies as object)
  if m.contentGrid = invalid or m.contentGrid.content = invalid then return
  
  moviesRow = m.contentGrid.content.getChild(0)
  if moviesRow = invalid then return
  
  ' Convert each movie to ContentNode
  for each movie in movies
    itemNode = CreateObject("roSGNode", "ContentNode")
    itemNode.title = movie.title
    itemNode.HDPosterUrl = GetPosterUrl(movie)
    itemNode.SDPosterUrl = GetPosterUrl(movie)
    itemNode.id = movie.id
    itemNode.json = FormatJson(movie)
    moviesRow.appendChild(itemNode)
  end for
  
  ' Update the RowList
  m.contentGrid.content = m.contentGrid.content
end sub

sub DisplayTVShows(shows as object)
  if m.contentGrid = invalid or m.contentGrid.content = invalid then return
  
  showsRow = m.contentGrid.content.getChild(1)
  if showsRow = invalid then return
  
  ' Convert each show to ContentNode
  for each show in shows
    itemNode = CreateObject("roSGNode", "ContentNode")
    itemNode.title = show.title
    itemNode.HDPosterUrl = GetPosterUrl(show)
    itemNode.SDPosterUrl = GetPosterUrl(show)
    itemNode.id = show.id
    itemNode.json = FormatJson(show)
    showsRow.appendChild(itemNode)
  end for
  
  ' Update the RowList
  m.contentGrid.content = m.contentGrid.content
end sub

function GetPosterUrl(item as object) as string
  ' Get poster from extra_json.poster or poster_url
  ej = invalid
  if item.extra_json <> invalid then
    ej = item.extra_json
  end if
  
  posterUrl = ""
  if ej <> invalid and ej.poster <> invalid then
    posterUrl = ej.poster
  else if item.poster_url <> invalid then
    posterUrl = item.poster_url
  end if
  
  ' Convert relative URLs to absolute
  if posterUrl <> "" then
    server_url = LoadServerUrl()
    if not (Left(posterUrl, 7) = "http://" or Left(posterUrl, 8) = "https://") then
      if Left(posterUrl, 1) = "/" then
        posterUrl = server_url + posterUrl
      else
        posterUrl = server_url + "/" + posterUrl
      end if
    end if
  end if
  
  return posterUrl
end function

sub onItemSelected(event as object)
  selectedIndex = event.getData()
  print "Item selected: " + selectedIndex.toStr()
  
  ' Get the selected row and item
  rowIndex = selectedIndex[0]
  itemIndex = selectedIndex[1]
  
  if m.contentGrid.content = invalid then return
  
  selectedRow = m.contentGrid.content.getChild(rowIndex)
  if selectedRow = invalid then return
  
  selectedItem = selectedRow.getChild(itemIndex)
  if selectedItem = invalid then return
  
  print "Selected: " + selectedItem.title
  
  ' Navigate to details (for now, just show in VideoScene)
  ' TODO: Create proper DetailsScene
  ShowVideoScene(selectedItem)
end sub

sub ShowVideoScene(item as object)
  print "Showing video scene for: " + item.title
  ' TODO: Implement navigation to VideoScene
  ' For now, this is a placeholder
end sub