function LoadTokens() as object
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  tokens = {}
  tokens.access_token = sec.Read("access_token")
  tokens.refresh_token = sec.Read("refresh_token")
  if tokens.access_token = invalid then tokens.access_token = ""
  if tokens.refresh_token = invalid then tokens.refresh_token = ""
  return tokens
end function

function LoadServerUrl() as string
  ' Load from registry (persistent storage)
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  url = sec.Read("server_url")
  if url = invalid then url = ""
  return url
end function

function HttpJson(url as string, method as string, body = invalid as dynamic, requiresAuth = false as boolean) as object
  req = CreateObject("roUrlTransfer")
  req.SetUrl(url)
  req.setCertificatesFile("common:/certs/ca-bundle.crt")
  req.InitClientCertificates()
  req.AddHeader("Accept", "application/json")
  req.SetTimeout(10)  ' 10 second timeout
  
  ' Add Bearer token if authentication required
  if requiresAuth then
    tokens = LoadTokens()
    if tokens.access_token <> "" then
      req.AddHeader("Authorization", "Bearer " + tokens.access_token)
    end if
  end if
  
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
