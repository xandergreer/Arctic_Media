sub init()
  print "PairingScene: init() called"
  
  ' Ensure labels exist before accessing them
  title = m.top.findNode("title")
  message = m.top.findNode("message")
  code = m.top.findNode("code")
  hint = m.top.findNode("hint")
  
  if title = invalid or message = invalid or code = invalid or hint = invalid then
    print "ERROR: Could not find all required UI nodes"
    return
  end if
  
  m.server_url = LoadServerUrl()
  m.device_code = invalid
  m.poll_timer = invalid
  m.reconnect_attempts = 0
  m.max_reconnect_attempts = 3
  
  ' If no server URL configured, show server input screen
  if m.server_url = invalid or m.server_url = "" then
    ' Show server URL input screen (we'll implement this)
    ShowServerInputScreen()
  else
    ' Start pairing with saved URL
    StartPairing()
  end if
end sub

sub ShowServerInputScreen()
  message = m.top.findNode("message")
  code = m.top.findNode("code")
  hint = m.top.findNode("hint")
  
  if message <> invalid then message.text = "Enter server URL:"
  if code <> invalid then code.text = "Press OK to configure"
  if hint <> invalid then hint.text = "Example: http://192.168.1.100:8085"
  
  ' Set up keyboard input (simplified - user presses OK to start)
  ' In a full implementation, you'd use a Keyboard component
  ' For now, we'll use a simple approach: try common URLs
  m.server_url = "http://192.168.1.100:8085"  ' Default, will be updated from server response
  StartPairing()
end sub

sub StartPairing()
  print "StartPairing() called, server_url=" + m.server_url
  
  message = m.top.findNode("message")
  code = m.top.findNode("code")
  hint = m.top.findNode("hint")
  
  if message <> invalid then message.text = "Requesting pairing code..."
  if code <> invalid then code.text = "---- ----"

  ' Ensure we have a server URL
  if m.server_url = invalid or m.server_url = "" then
    m.server_url = LoadServerUrl()
    if m.server_url = invalid or m.server_url = "" then
      ' Last resort: try localhost (won't work for remote Roku, but for testing)
      m.server_url = "http://127.0.0.1:8085"
    end if
  end if

  RequestPairing()
end sub

sub RequestPairing()
  print "RequestPairing() called, server_url=" + m.server_url
  
  message = m.top.findNode("message")
  code = m.top.findNode("code")
  hint = m.top.findNode("hint")
  
  if message <> invalid then message.text = "Requesting pairing code..."
  if code <> invalid then code.text = "---- ----"

  url = m.server_url + "/pair/request"
  body = {}
  json = HttpJson(url, "POST", body)
  
  if json = invalid or json.device_code = invalid then
    m.reconnect_attempts = m.reconnect_attempts + 1
    if m.reconnect_attempts <= m.max_reconnect_attempts then
      ' Try alternative server URLs
      if m.reconnect_attempts = 1 then
        m.server_url = "http://192.168.1.100:8085"
      else if m.reconnect_attempts = 2 then
        m.server_url = "http://192.168.1.1:8085"
      else
        m.server_url = "http://127.0.0.1:8085"
      end if
      print "Retrying with server URL: " + m.server_url
      RequestPairing()
      return
    end if
    
    if message <> invalid then message.text = "Failed to get pairing code"
    if hint <> invalid then hint.text = "Server URL: " + m.server_url + " (configure in server settings)"
    if code <> invalid then code.text = "ERROR"
    print "ERROR: Failed to get pairing code from " + m.server_url
    return
  end if

  ' Reset reconnect attempts on success
  m.reconnect_attempts = 0

  m.device_code = json.device_code
  user_code = json.user_code
  m.expires_in = json.expires_in
  m.poll_interval = json.interval
  
  ' CRITICAL: Always use and save the server_url from the server's response
  ' This ensures we use the correct dynamic URL (IP, domain, port) configured by admin
  if json.server_url <> invalid and json.server_url <> "" then
    new_url = json.server_url
    ' Only update if URL changed (prevents unnecessary registry writes)
    if new_url <> m.server_url then
      print "Server URL changed from " + m.server_url + " to " + new_url
      SaveServerUrl(new_url)
      m.server_url = new_url
    end if
  end if

  ' Display user code
  if message <> invalid then message.text = "Enter this code on your server:"
  if code <> invalid then code.text = user_code
  if hint <> invalid then hint.text = "Go to " + m.server_url + "/pair"

  ' Start polling
  m.poll_timer = CreateObject("roSGNode", "Timer")
  m.poll_timer.repeat = true
  m.poll_timer.duration = m.poll_interval
  m.poll_timer.observeField("fire", "OnPollTimer")
  m.poll_timer.control = "start"
end sub

sub OnPollTimer(event)
  if m.device_code = invalid then return
  
  ' Always reload server URL from registry in case it changed
  saved_url = LoadServerUrl()
  if saved_url <> invalid and saved_url <> "" and saved_url <> m.server_url then
    print "Server URL changed detected: " + m.server_url + " -> " + saved_url
    m.server_url = saved_url
    ' Restart pairing with new URL
    if m.poll_timer <> invalid then m.poll_timer.control = "stop"
    StartPairing()
    return
  end if
  
  ' Ensure we have a valid server URL
  if m.server_url = invalid or m.server_url = "" then
    m.server_url = LoadServerUrl()
    if m.server_url = invalid or m.server_url = "" then
      m.top.findNode("message").text = "Server URL lost. Restart app."
      if m.poll_timer <> invalid then m.poll_timer.control = "stop"
      return
    end if
  end if

  url = m.server_url + "/pair/poll"
  body = { device_code: m.device_code }
  json = HttpJson(url, "POST", body)

  if json = invalid then 
    ' Connection failed - server URL might have changed
    ' Try to reload URL and retry next time
    saved_url = LoadServerUrl()
    if saved_url <> invalid and saved_url <> "" and saved_url <> m.server_url then
      print "Connection failed, server URL may have changed. Reloading..."
      m.server_url = saved_url
    end if
    return
  end if

  ' Check if server returned a new server_url (server IP changed)
  if json.server_url <> invalid and json.server_url <> "" and json.server_url <> m.server_url then
    print "Server returned new URL: " + json.server_url + " (was " + m.server_url + ")"
    SaveServerUrl(json.server_url)
    m.server_url = json.server_url
  end if

  if json.status = "authorized" then
    ' Save tokens
    SaveTokens(json.access_token, json.refresh_token)
    ' Navigate to home
    m.top.findNode("message").text = "Authorized! Loading..."
    if m.poll_timer <> invalid then m.poll_timer.control = "stop"
    
    ' Restart app with HomeScene (Roku doesn't support dynamic scene switching easily)
    ' So we just show success message - user will restart manually
    print "Authorized! User should restart app to see home content"
    
    ' Alternative: Set a flag and have main.brs check it
    ' For now, simple approach: show success
  else if json.status = "pending" then
    ' Keep waiting
  else
    m.top.findNode("message").text = "Pairing failed or expired"
    if m.poll_timer <> invalid then m.poll_timer.control = "stop"
  end if
end sub

sub SaveServerUrl(url as string)
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  sec.Write("server_url", url)
  sec.Flush()
  print "Saved server URL: " + url
end sub

sub SaveTokens(access_token as string, refresh_token as string)
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  sec.Write("access_token", access_token)
  sec.Write("refresh_token", refresh_token)
  sec.Flush()
  print "Saved authentication tokens"
end sub
