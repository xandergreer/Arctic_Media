sub init()
    m.lbl = m.top.findNode("lbl")
    m.bg = m.top.findNode("bg")
    m.underline = m.top.findNode("underline")
    
    m.top.focusable = true
    m.top.observeField("focusedChild", "OnFocusChange")
end sub

sub OnTextChanged()
    m.lbl.text = m.top.text
    ' Adjust width if needed? For now keeps fixed width or uses minWidth in LayoutGroup
    ' If LayoutGroup handles it, we might need to expose width?
    ' We set width=150 in XML.
end sub

sub OnFocusChange()
    if m.top.hasFocus()
        ' Active State
        m.lbl.color = "#FFFFFF" 
        m.lbl.font = "font:MediumBoldSystemFont"
        
        ' Animate Underline? 
        ' For now direct set
        m.underline.visible = true
        m.underline.width = 180
        m.underline.translation = [35, 45] ' Centered under 250 width (250-180)/2 = 35
    else
        ' Inactive State
        m.lbl.color = "#888888"
        m.lbl.font = "font:MediumSystemFont"
        m.underline.visible = false
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
