sub init()
    m.btnRefresh = m.top.findNode("btnRefresh")
    m.btnLogout = m.top.findNode("btnLogout")
    m.btnClose = m.top.findNode("btnClose")
    
    m.serverInfo = m.top.findNode("serverInfo")
    
    m.btnRefresh.observeField("buttonSelected", "OnRefresh")
    m.btnLogout.observeField("buttonSelected", "OnLogout")
    m.btnClose.observeField("buttonSelected", "OnClose")
    
    m.top.observeField("server_url", "OnInfoReady")
    m.top.observeField("focusedChild", "OnFocusChange")
end sub

sub OnFocusChange()
    if m.top.hasFocus()
        m.btnRefresh.setFocus(true)
    end if
end sub

sub OnInfoReady()
    if m.top.server_url <> ""
        m.serverInfo.text = "Connected to: " + m.top.server_url
    end if
end sub

sub OnRefresh()
    TriggerRefresh()
end sub

sub OnLogout()
    print "Logout selected"
    ClearTokens()
    m.top.logout_triggered = true
end sub

sub OnClose()
    m.top.wasClosed = true
end sub

sub TriggerRefresh()
    m.btnRefresh.text = "Requesting Scan..." ' Visual feedback on button
    ' ... rest keeps same logic ...
    
    task = CreateObject("roSGNode", "NetworkTask")
    task.url = m.top.server_url + "/libraries/scan_all?background=true&refresh_metadata=true"
    task.method = "POST"
    task.headers = { "Authorization": "Bearer " + m.top.auth_token }
    task.observeField("response", "OnRefreshResponse")
    task.control = "RUN"
    
    m.refreshTask = task
end sub

sub OnRefreshResponse(event)
    response = event.getData()
    if response <> invalid and response.status <> "error"
        m.btnRefresh.text = "Scan Started!"
    else
        msg = "Error"
        if response <> invalid and response.message <> invalid then msg = response.message
        m.btnRefresh.text = "Failed: " + msg
    end if
    m.refreshTask = invalid
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    
    if key = "back"
        m.top.wasClosed = true
        return true
    end if
    
    if key = "down"
        if m.btnRefresh.hasFocus()
            m.btnLogout.setFocus(true)
        else if m.btnLogout.hasFocus()
            m.btnClose.setFocus(true)
        end if
        return true
    else if key = "up"
         if m.btnClose.hasFocus()
            m.btnLogout.setFocus(true)
         else if m.btnLogout.hasFocus()
            m.btnRefresh.setFocus(true)
         end if
         return true
    end if
    
    return false
end function
