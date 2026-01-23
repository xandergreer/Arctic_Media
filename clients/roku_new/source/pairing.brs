sub init()
  print "PairingScene: init() called"
  m.pairingGroup = m.top.findNode("pairingGroup")
  m.manualEntryGroup = m.top.findNode("manualEntryGroup")
  m.ipInputDisplay = m.top.findNode("ipInputDisplay")
  m.btnEdit = m.top.findNode("btnEdit")
  m.connectButton = m.top.findNode("connectButton")

  ' Inline load url logic
  url = ""
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  if sec.Exists("server_url") then url = sec.Read("server_url")
  if url = "" then url = "https://arcticmedia.space"
  m.server_url = url
  m.current_input_text = url
  
  if m.ipInputDisplay <> invalid then m.ipInputDisplay.text = url

  ' Observers
  if m.btnEdit <> invalid then
    m.btnEdit.observeField("buttonSelected", "OnEditButtonSelected")
  end if
  if m.connectButton <> invalid then
    m.connectButton.observeField("buttonSelected", "OnConnectButtonSelected")
  end if

  m.startup_timer = CreateObject("roSGNode", "Timer")
  m.startup_timer.duration = 0.5
  m.startup_timer.repeat = false
  m.startup_timer.observeField("fire", "OnStartup")
  m.startup_timer.control = "start"
end sub

sub OnStartup()
  print "OnStartup: Enforcing Visibility and Focus"
  ShowServerInputScreen()
end sub

sub ShowServerInputScreen()
  if m.manualEntryGroup <> invalid then m.manualEntryGroup.visible = true
  if m.pairingGroup <> invalid then m.pairingGroup.visible = false
  
  if m.connectButton <> invalid then
      print "Setting focus to Connect Button"
      m.connectButton.setFocus(true)
  end if
end sub

sub OnEditButtonSelected()
    print "Edit Button Selected - Opening Dialog"
    dialog = CreateObject("roSGNode", "KeyboardDialog")
    dialog.title = "Enter Server Address"
    dialog.text = m.current_input_text
    dialog.buttons = ["OK", "Cancel"]
    dialog.observeField("buttonSelected", "OnDialogButton")
    m.top.dialog = dialog
end sub

sub OnDialogButton(event)
    dialog = event.getRoSGNode()
    idx = event.getData()
    text = dialog.text
    if idx = 0 then
        m.current_input_text = text
        if m.ipInputDisplay <> invalid then m.ipInputDisplay.text = text
        m.server_url = text
        dialog.close = true
        if m.connectButton <> invalid then m.connectButton.setFocus(true)
    else
        dialog.close = true
        if m.btnEdit <> invalid then m.btnEdit.setFocus(true)
    end if
end sub

sub OnConnectButtonSelected()
    ' User clicked "Connect"
    ip = m.current_input_text.Trim()
    
    if ip = "" then ip = "https://arcticmedia.space"
    
    if ip <> "" then
       url = ip
       
      ' URL Logic inline
      if LCase(Left(url, 7)) <> "http://" and LCase(Left(url, 8)) <> "https://" then
         url = "http://" + url
      end if
      
      is_https = (LCase(Left(url, 8)) = "https://")
      
      num_colons = 0
      for i = 1 to Len(url)
          if Mid(url, i, 1) = ":" then num_colons = num_colons + 1
      end for
      
      if num_colons < 2 and not is_https then
          url = url + ":8085"
      end if
      
      print "User entered: " + ip + " -> Parsed URL: " + url
      
      ' INLINE SAVE
      sec = CreateObject("roRegistrySection", "ArcticMedia")
      sec.Write("server_url", url)
      sec.Flush()
      print "Saved server URL: " + url
      
      m.server_url = url
      
      ' INLINE START PAIRING LOGICI
      if m.manualEntryGroup <> invalid then m.manualEntryGroup.visible = false
      if m.pairingGroup <> invalid then m.pairingGroup.visible = true
      
      print "StartPairing (INLINED)"
      
      msg = m.top.findNode("message")
      code = m.top.findNode("code")
      if msg <> invalid then msg.text = "Requests pairing..."
      if code <> invalid then code.text = "LOADING"
      
      m.countdown_value = 15
      m.timeout_timer = CreateObject("roSGNode", "Timer")
      m.timeout_timer.duration = 1
      m.timeout_timer.repeat = true
      m.timeout_timer.observeField("fire", "OnCountdownTimer")
      m.timeout_timer.control = "start"
      
      ' INLINE REQUEST TASK
      print "Starting Pairing Network Task..."
      m.pairingTask = CreateObject("roSGNode", "NetworkTask")
      if m.pairingTask = invalid then
          print "CRITICAL ERROR: Could not create NetworkTask node!"
          if msg <> invalid then msg.text = "Error: App Install Corrupt (Task Missing)"
          return
      end if
      
      m.pairingTask.setField("url", m.server_url + "/pair/request")
      m.pairingTask.setField("method", "POST")
      m.pairingTask.setField("body", {})
      m.pairingTask.observeField("response", "OnPairingResponse")
      m.pairingTask.observeField("debugMsg", "OnTaskDebugMsg")
      m.pairingTask.control = "RUN"
   end if
end sub

sub OnCountdownTimer()
  m.countdown_value = m.countdown_value - 1
  state = "NONE"
  if m.pairingTask <> invalid then state = m.pairingTask.state
  code = m.top.findNode("code")
  if code <> invalid then code.text = "WAIT [" + m.countdown_value.ToStr() + "] " + state
  if m.countdown_value <= 0 then OnConnectionTimeout()
end sub

sub OnConnectionTimeout()
    print "Pairing Connection Timeout"
    if m.pairingTask <> invalid then m.pairingTask.control = "STOP"
    if m.timeout_timer <> invalid then m.timeout_timer.control = "stop"
    msg = m.top.findNode("message")
    if msg <> invalid then msg.text = "Connection Timed Out. Please check IP."
    ShowServerInputScreen()
end sub

sub OnTaskDebugMsg(event)
    msg = event.getData()
    print "Task Debug: " + msg
    label = m.top.findNode("message")
    if label <> invalid then label.text = msg
end sub

sub OnPairingResponse(event)
    response = event.getData()
    print "Pairing Response Received"
    if m.timeout_timer <> invalid then m.timeout_timer.control = "stop"
    
    if response = invalid or response.status = "error" then
         err_msg = "Unknown Error"
         if response <> invalid and response.message <> invalid then err_msg = response.message
         print "Pairing Task Failed: " + err_msg
         
         ' Reconnect Logic - simplified inline
         m.reconnect_attempts = m.reconnect_attempts + 1
         if m.reconnect_attempts <= 1 then
             print "Retrying... " + m.reconnect_attempts.ToStr()
             ' Re-trigger task creation by calling OnConnectButtonSelected? No, bad recursion.
             ' Duplicate logic here briefly or just fail for now to be safe.
             ' Let's just fail to input screen for safety.
             ShowServerInputScreen()
             errLabel = m.top.findNode("errorLabel")
             if errLabel <> invalid then errLabel.text = "Error: " + err_msg
             return
         end if
         
         ShowServerInputScreen()
         errLabel = m.top.findNode("errorLabel")
         if errLabel <> invalid then errLabel.text = "Error: " + err_msg
         return
    end if
    
    m.reconnect_attempts = 0
    m.device_code = response.device_code
    m.top.findNode("message").text = "Enter this code on your server:"
    m.top.findNode("code").text = response.user_code
    m.top.findNode("hint").text = "Go to " + m.server_url + "/pair"
    
    m.poll_interval = response.interval
    m.poll_timer = CreateObject("roSGNode", "Timer")
    m.poll_timer.repeat = true
    m.poll_timer.duration = m.poll_interval
    m.poll_timer.observeField("fire", "OnPollTimer")
    m.poll_timer.control = "start"
end sub

sub OnPollTimer()
    task = CreateObject("roSGNode", "NetworkTask")
    task.setField("url", m.server_url + "/pair/poll")
    task.setField("method", "POST")
    task.setField("body", { device_code: m.device_code })
    task.observeField("response", "OnPollResponse")
    task.control = "RUN"
end sub

sub OnPollResponse(event)
    response = event.getData()
    if response = invalid or response.status = "error" then
        print "Poll failed"
        return
    end if
    if response.status = "authorized" then
        ' INLINE SAVE TOKENS
        sec = CreateObject("roRegistrySection", "ArcticMedia")
        sec.Write("access_token", response.access_token)
        sec.Write("refresh_token", response.refresh_token)
        sec.Flush()
        print "Saved authentication tokens (Inline)"

        m.top.findNode("message").text = "Authorized! Loading Home..."
        m.top.findNode("code").text = "SUCCESS"
        if m.poll_timer <> invalid then m.poll_timer.control = "stop"
        m.top.pairing_finished = true
    else if response.status = "pending" then
    else 
        m.top.findNode("message").text = "Expired/Failed"
        if m.poll_timer <> invalid then m.poll_timer.control = "stop"
    end if
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if press then
        print "Key Pressed: " + key
        
        if key = "back" then return false
        
        ' Manual Navigation Override
        if key = "up" or key = "down" then
             if m.connectButton <> invalid and m.connectButton.hasFocus() then
                 if m.btnEdit <> invalid then m.btnEdit.setFocus(true)
                 return true
             else if m.btnEdit <> invalid and m.btnEdit.hasFocus() then
                 if m.connectButton <> invalid then m.connectButton.setFocus(true)
                 return true
             end if
        end if
        
        ' Manual Activation Override
        if key = "OK" or key = "Select" then
             if m.connectButton <> invalid and m.connectButton.hasFocus() then
                 print "Forcing Connect Selection"
                 OnConnectButtonSelected()
                 return true
             else if m.btnEdit <> invalid and m.btnEdit.hasFocus() then
                 print "Forcing Edit Selection"
                 OnEditButtonSelected()
                 return true
             end if
        end if
    end if
    return false
end function
