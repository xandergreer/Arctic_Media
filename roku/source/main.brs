' Import API utilities
function LoadTokens() as object
  sec = CreateObject("roRegistrySection", "ArcticMedia")
  tokens = {}
  tokens.access_token = sec.Read("access_token")
  tokens.refresh_token = sec.Read("refresh_token")
  if tokens.access_token = invalid then tokens.access_token = ""
  if tokens.refresh_token = invalid then tokens.refresh_token = ""
  return tokens
end function

sub main()
    print "Arctic Media: Starting app"
    
    ' Check if already authenticated
    tokens = LoadTokens()
    if tokens.access_token <> "" then
        print "Already authenticated, going to HomeScene"
        sceneToLoad = "HomeScene"
    else
        print "Not authenticated, going to PairingScene"
        sceneToLoad = "PairingScene"
    end if
    
    ' Create screen and port
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.setMessagePort(port)
    
    ' Load the appropriate scene
    print "Loading scene: " + sceneToLoad
    scene = screen.CreateScene(sceneToLoad)
    if scene = invalid then
        print "ERROR: Failed to create " + sceneToLoad
        return
    end if
    
    print "Showing screen..."
    screen.Show()

    while true
        msg = wait(0, port)
        if type(msg) = "roSGScreenEvent" then
            if msg.isScreenClosed() then 
                print "Screen closed"
                return
            end if
            if msg.isRemoteKeyPressed() then
                key = msg.getIndex()
                print "Key pressed: " + key.toStr()
            end if
        end if
    end while
end sub