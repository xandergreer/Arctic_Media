sub main()
    print "Arctic Media: Starting app"
    
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.setMessagePort(port)
    
    ' Check auth
    sec = CreateObject("roRegistrySection", "ArcticMedia")
    authToken = sec.Read("access_token")
    
    scene = invalid
    
    if authToken <> invalid and authToken <> "" then
        print "Already authenticated, loading Home..."
        scene = screen.CreateScene("HomeScene")
        scene.server_url = sec.Read("server_url")
        scene.auth_token = authToken
        scene.observeField("logout_requested", port)
    else
        print "Not authenticated, loading Pairing..."
        scene = screen.CreateScene("PairingScene")
        scene.observeField("pairing_finished", port) ' Notify port when finished
    end if
    
    screen.Show()

    while true
        msg = wait(0, port)
        msgType = type(msg)
        
        if msgType = "roSGScreenEvent" then
            if msg.isScreenClosed() then return
        else if msgType = "roSGNodeEvent"
            field = msg.getField()
            if field = "pairing_finished"
                print "Pairing finished! Switching to HomeScene..."
                
                ' Reload auth data
                sec = CreateObject("roRegistrySection", "ArcticMedia")
                authToken = sec.Read("access_token")
                serverUrl = sec.Read("server_url")
                
                ' Create HomeScene
                homeScene = screen.CreateScene("HomeScene")
                homeScene.server_url = serverUrl
                homeScene.auth_token = authToken
                homeScene.observeField("logout_requested", port)
                
                ' Replace Scene
                screen.Show() 
                ' Note: Calling Show() with a new scene created via CreateScene sets it as active? 
                ' No, CreateScene just creates it. We need to handle this carefully.
                ' Actually, Roku documents say: "If you call CreateScene again, it replaces the existing scene."
                
                
                scene = homeScene
            else if field = "logout_requested"
                print "Logout requested! Switching to PairingScene..."
                
                pScene = screen.CreateScene("PairingScene")
                pScene.observeField("pairing_finished", port)
                screen.Show()
                scene = pScene
            end if
        end if
    end while
end sub
