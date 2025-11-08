//
//  PlayerView.swift
//  ArcticMedia
//

import SwiftUI
import AVKit

struct PlayerView: View {
    let itemId: String
    let title: String
    let episode: Episode?
    
    init(itemId: String, title: String) {
        self.itemId = itemId
        self.title = title
        self.episode = nil
    }
    
    init(episode: Episode) {
        self.episode = episode
        self.itemId = episode.first_file_id ?? ""
        self.title = episode.title
    }
    
    var body: some View {
        Group {
            if let url = streamingURL {
                VideoPlayer(player: AVPlayer(url: url))
                    .edgesIgnoringSafeArea(.all)
            } else {
                VStack {
                    Text("Unable to load video")
                        .foregroundColor(.secondary)
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var streamingURL: URL? {
        guard !itemId.isEmpty else { return nil }
        return APIService.shared.getStreamingURL(itemId: itemId)
    }
}

