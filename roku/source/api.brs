function HttpJson(url as string, method as string, body = invalid as dynamic, token = invalid as string) as object
  req = CreateObject("roUrlTransfer")
  req.SetUrl(url)
  req.setCertificatesFile("common:/certs/ca-bundle.crt")
  req.InitClientCertificates()
  req.AddHeader("Accept", "application/json")
  if token <> invalid and token <> "" then
    req.AddHeader("Authorization", "Bearer " + token)
  end if
  req.SetTimeout(15)  ' 15 second timeout
  
  json_str = ""
  if body <> invalid and type(body) = "roAssociativeArray" then
    if method = "POST" then req.AddHeader("Content-Type", "application/json")
    json_str = FormatJson(body)
  else
    json_str = "{}"
  end if

  print "HTTP " + method + " " + url
  rsp = invalid
  if method = "POST" then
    rsp = req.PostFromString(json_str)
  else
    rsp = req.GetToString()
  end if

  if rsp = invalid or rsp = "" then
    print "HTTP request failed or empty response"
    return invalid
  end if
  
  print "HTTP response: " + Left(rsp, 200)  ' First 200 chars for debugging
  parser = CreateObject("roJsonParser")
  return parser.Parse(rsp)
end function

function FormatJson(obj as dynamic) as string
  ' Simple JSON encoding for Roku (limited support)
  if type(obj) = "roAssociativeArray" then
    parts = []
    for each key in obj
      val = obj[key]
      if type(val) = "String" then
        parts.push(Chr(34) + key + Chr(34) + ": " + Chr(34) + val + Chr(34))
      else if type(val) = "Integer" or type(val) = "LongInteger" then
        parts.push(Chr(34) + key + Chr(34) + ": " + val.ToStr())
      else if type(val) = "Boolean" then
        parts.push(Chr(34) + key + Chr(34) + ": " + iif(val, "true", "false"))
      end if
    end for
    result = ""
    for i = 0 to parts.count() - 1
      if result <> "" then result = result + ","
      result = result + parts[i]
    end for
    return "{" + result + "}"
  end if
  return "{}"
end function

function GetServerUrl() as string
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  url = sec.Read("server_url")
  if url = invalid then url = ""
  return url
end function

function GetAuthToken() as string
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  token = sec.Read("access_token")
  if token = invalid then token = ""
  return token
end function

function ApiGetMovies(serverUrl as string, token as string, page = 1 as integer, pageSize = 50 as integer) as object
  url = serverUrl + "/api/movies?page=" + page.ToStr() + "&page_size=" + pageSize.ToStr()
  return HttpJson(url, "GET", invalid, token)
end function

function ApiGetTVShows(serverUrl as string, token as string, page = 1 as integer, pageSize = 50 as integer) as object
  url = serverUrl + "/api/tv?page=" + page.ToStr() + "&page_size=" + pageSize.ToStr()
  return HttpJson(url, "GET", invalid, token)
end function

function ApiGetSeasons(serverUrl as string, token as string, showId as string) as object
  url = serverUrl + "/api/tv/seasons?show_id=" + showId
  return HttpJson(url, "GET", invalid, token)
end function

function ApiGetEpisodes(serverUrl as string, token as string, showId as string, season as integer) as object
  url = serverUrl + "/api/tv/episodes?show_id=" + showId + "&season=" + season.ToStr()
  return HttpJson(url, "GET", invalid, token)
end function

function ApiGetMediaFiles(serverUrl as string, token as string, mediaId as string) as object
  url = serverUrl + "/api/media/" + mediaId + "/files"
  return HttpJson(url, "GET", invalid, token)
end function

function GetStreamingUrl(serverUrl as string, itemId as string, token as string) as string
  ' Return HLS master playlist URL for streaming
  return serverUrl + "/stream/" + itemId + "/master.m3u8?container=fmp4&token=" + token
end function

function GetPosterUrl(serverUrl as string, posterPath as string) as string
  if posterPath = invalid or posterPath = "" then return ""
  if Left(posterPath, 4) = "http" then return posterPath
  if Left(posterPath, 1) = "/" then return serverUrl + posterPath
  return serverUrl + "/" + posterPath
end function
