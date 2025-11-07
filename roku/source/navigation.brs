' Navigation helper functions
function NavigateToScene(sceneName as string, data = invalid as dynamic)
  ' Access global node through scene
  globalNode = m.top.getScene().getGlobalNode()
  if globalNode <> invalid then
    globalNode.addFields({ nextScene: sceneName, sceneData: data })
    globalNode.setField("sceneChange", sceneName)
  end if
end function

function GetNavigationData() as dynamic
  globalNode = m.top.getScene().getGlobalNode()
  if globalNode <> invalid then
    return globalNode.sceneData
  end if
  return invalid
end function

