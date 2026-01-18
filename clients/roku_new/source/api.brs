function LoadTokens() as object
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  tokens = {}
  tokens.access_token = sec.Read("access_token")
  tokens.refresh_token = sec.Read("refresh_token")
  if tokens.access_token = invalid then tokens.access_token = ""
  if tokens.refresh_token = invalid then tokens.refresh_token = ""
  if tokens.refresh_token = invalid then tokens.refresh_token = ""
  return tokens
end function

function ClearTokens()
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  sec.Delete("access_token")
  sec.Delete("refresh_token")
  sec.Flush()
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
  
  code = req.GetResponseCode()
  print "HTTP Status: " + code.toStr()

  if code = 401
    return { "status": "error", "code": 401, "message": "Unauthorized" }
  end if

  if rsp = invalid or rsp = "" then
    print "HTTP request failed or empty response"
    return { "status": "error", "code": code, "message": "Request failed" }
  end if
  
  print "HTTP response: " + Left(rsp, 200)  ' First 200 chars for debugging
  parser = CreateObject("roJsonParser")
  json = parser.Parse(rsp)
  
  if json = invalid
     return { "status": "error", "code": code, "message": "Invalid JSON" }
  end if
  
  return json
end function

function FormatJson(obj as dynamic) as string
  if obj = invalid then return "null"
  if type(obj) = "roString" or type(obj) = "String" then return Chr(34) + obj + Chr(34)
  if type(obj) = "roInt" or type(obj) = "Integer" or type(obj) = "LongInteger" then return obj.toStr()
  if type(obj) = "roBoolean" or type(obj) = "Boolean" then 
    if obj then return "true" else return "false"
  end if
  
  if type(obj) = "roArray" then
    res = "["
    for i = 0 to obj.Count() - 1
      if i > 0 then res = res + ","
      res = res + FormatJson(obj[i])
    end for
    return res + "]"
  end if

  if type(obj) = "roAssociativeArray" then
    res = "{"
    first = true
    for each key in obj
      if not first then res = res + ","
      res = res + Chr(34) + key + Chr(34) + ":" + FormatJson(obj[key])
      first = false
    end for
    return res + "}"
  end if
  
  return "null"
end function

function iif(condition, trueVal, falseVal)
    if condition then return trueVal else return falseVal
end function
