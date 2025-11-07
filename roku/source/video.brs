sub init()
  m.videoPlayer = m.top.findNode("videoPlayer")
  
  m.serverUrl = GetServerUrl()
  m.token = GetAuthToken()
  
  ' Get data from navigation
  data = GetNavigationData()
  if data <> invalid then
    m.itemId = data.itemId
    m.itemType = data.itemType
    StartPlayback()
  end if
  
  ' Set up video player observers
  m.videoPlayer.observeField("state", "OnVideoState")
  m.videoPlayer.observeField("position", "OnVideoPosition")
  
  m.top.setFocus(true)
end sub

sub StartPlayback()
  if m.itemId = invalid or m.itemId = "" then return
  
  ' Get streaming URL
  streamUrl = GetStreamingUrl(m.serverUrl, m.itemId, m.token)
  
  print "Starting playback: " + streamUrl
  
  ' Create video content
  content = CreateObject("roSGNode", "ContentNode")
  content.url = streamUrl
  content.streamFormat = "hls"
  content.title = "Playing..."
  
  m.videoPlayer.content = content
  m.videoPlayer.control = "play"
  m.videoPlayer.setFocus(true)
end sub

sub OnVideoState()
  state = m.videoPlayer.state
  print "Video state: " + state
  
  if state = "error" then
    print "Video playback error"
    ' Return to previous screen
    NavigateToScene("HomeScene", invalid)
  else if state = "finished" then
    ' Return to previous screen when finished
    NavigateToScene("HomeScene", invalid)
  end if
end sub

sub OnVideoPosition()
  ' Could save playback position here if needed
end sub

function onKeyEvent(key as string, press as boolean) as boolean
  if not press then return false
  
  if key = "back" then
    ' Stop playback and return
    m.videoPlayer.control = "stop"
    NavigateToScene("HomeScene", invalid)
    return true
  else if key = "play" or key = "OK" then
    ' Pause/resume
    if m.videoPlayer.state = "playing" then
      m.videoPlayer.control = "pause"
    else
      m.videoPlayer.control = "resume"
    end if
    return true
  end if
  
  return false
end function

