sub main()
    print "Arctic Media: Starting app"
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.setMessagePort(port)
    
    print "Creating PairingScene..."
    scene = screen.CreateScene("PairingScene")
    if scene = invalid then
        print "ERROR: Failed to create PairingScene"
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
        end if
    end while
end sub
