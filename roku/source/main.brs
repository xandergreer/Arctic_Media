sub main()
    print "Arctic Media: Starting app"
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.setMessagePort(port)
    
    ' Create global node for navigation
    m.global = screen.getGlobalNode()
    m.global.addFields({ nextScene: "", sceneData: invalid, sceneChange: "" })
    
    ' Store screen reference globally for navigation
    m.screen = screen
    
    ' Check if we have tokens
    tokens = LoadTokens()
    currentScene = "PairingScene"
    if tokens <> invalid and tokens.access_token <> invalid and tokens.access_token <> "" then
        ' We have tokens, go to home
        currentScene = "HomeScene"
    end if
    
    print "Creating " + currentScene + "..."
    scene = screen.CreateScene(currentScene)
    if scene = invalid then
        print "ERROR: Failed to create " + currentScene
        return
    end if
    
    print "Showing screen..."
    screen.Show()
    
    ' Observe scene changes
    m.global.observeField("sceneChange", "OnSceneChange")

    while true
        msg = wait(0, port)
        if type(msg) = "roSGScreenEvent" then
            if msg.isScreenClosed() then 
                print "Screen closed"
                return
            end if
        else if type(msg) = "roSGNodeEvent" then
            if msg.getField() = "sceneChange" then
                OnSceneChange(msg)
            end if
        end if
    end while
end sub

sub OnSceneChange(msg)
    nextSceneName = m.global.nextScene
    if nextSceneName = invalid or nextSceneName = "" then return
    
    print "Navigating to: " + nextSceneName
    scene = m.screen.CreateScene(nextSceneName)
    if scene <> invalid then
        m.screen.setScene(scene)
    else
        print "ERROR: Failed to create scene: " + nextSceneName
    end if
end sub

function LoadTokens() as object
    sec = CreateObject("roRegistrySection", "ArcticMedia")
    tokens = {}
    tokens.access_token = sec.Read("access_token")
    tokens.refresh_token = sec.Read("refresh_token")
    if tokens.access_token = invalid then tokens.access_token = ""
    if tokens.refresh_token = invalid then tokens.refresh_token = ""
    return tokens
end function
