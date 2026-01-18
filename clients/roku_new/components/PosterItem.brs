sub init()
    m.itemPoster = m.top.findNode("itemPoster")
    m.itemLabel = m.top.findNode("itemLabel")
    print "PosterItem Init"
end sub

sub itemContentChanged()
    itemData = m.top.itemContent
    if itemData <> invalid
        print "PosterItem Content: " + itemData.title
        m.itemPoster.uri = itemData.hdposterurl
        m.itemLabel.text = itemData.title
    else
        print "PosterItem Content Invalid"
    end if
end sub

sub widthChanged()
    m.itemPoster.width = m.top.width
    m.itemLabel.width = m.top.width
end sub

sub heightChanged()
    ' Adjust height if needed, usually fixed by parent MarkupGrid
    ' For now, assume fixed height for poster within cell
    m.itemPoster.height = m.top.height - 40 ' Reserve space for label
    m.itemLabel.translation = [0, m.top.height - 30]
end sub
