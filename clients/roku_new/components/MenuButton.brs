sub init()
    m.lbl = m.top.findNode("lbl")
    m.bg = m.top.findNode("bg")
    m.focusInd = m.top.findNode("focusInd")
    
    m.top.focusable = true
    m.top.observeField("focusedChild", "OnFocusChange")
end sub

sub OnTextChanged()
    m.lbl.text = m.top.text
end sub

sub OnFocusChange()
    if m.top.hasFocus()
        ' Active State
        m.lbl.color = "#FFFFFF" 
        m.lbl.font = "font:MediumBoldSystemFont"
        m.focusInd.visible = true
    else
        ' Inactive State
        m.lbl.color = "#888888"
        m.lbl.font = "font:MediumSystemFont"
        m.focusInd.visible = false
    end if
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press return false
    
    if key = "OK"
        m.top.buttonSelected = true
        return true
    end if
    
    return false
end function
