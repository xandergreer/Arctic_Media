//
//  HomeView.swift
//  ArcticMedia
//

import SwiftUI

struct HomeView: View {
    @State private var recentMovies: [MediaItem] = []
    @State private var recentTVShows: [TVShow] = []
    @State private var isLoading: Bool = true
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding()
                    } else {
                        if !recentMovies.isEmpty {
                            SectionView(title: "Recent Movies", items: recentMovies.map { MediaItemWrapper($0) })
                        }
                        
                        if !recentTVShows.isEmpty {
                            SectionView(title: "Recent TV Shows", items: recentTVShows.map { TVShowWrapper($0) })
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Arctic Media")
            .task {
                await loadRecentContent()
            }
        }
    }
    
    private func loadRecentContent() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            async let movies = APIService.shared.getMovies(page: 1, pageSize: 20, sort: "recent")
            async let shows = APIService.shared.getTVShows(page: 1, pageSize: 20, sort: "recent")
            
            let moviesResult = try await movies
            let showsResult = try await shows
            
            await MainActor.run {
                recentMovies = moviesResult.items
                recentTVShows = showsResult.items
            }
        } catch {
            print("Error loading content: \(error)")
        }
    }
}

// Wrapper types for protocol conformance
struct MediaItemWrapper: Identifiable {
    let id: String
    let title: String
    let posterURL: URL?
    let item: MediaItem
    
    init(_ item: MediaItem) {
        self.item = item
        self.id = item.id
        self.title = item.title
        self.posterURL = item.posterURL
    }
}

struct TVShowWrapper: Identifiable {
    let id: String
    let title: String
    let posterURL: URL?
    let show: TVShow
    
    init(_ show: TVShow) {
        self.show = show
        self.id = show.id
        self.title = show.title
        self.posterURL = show.posterURL
    }
}

struct SectionView: View {
    let title: String
    let items: [any Identifiable & HasPoster]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.title2)
                .fontWeight(.bold)
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(items, id: \.id) { item in
                        PosterCard(item: item)
                    }
                }
            }
        }
    }
}

protocol HasPoster {
    var id: String { get }
    var title: String { get }
    var posterURL: URL? { get }
}

extension MediaItemWrapper: HasPoster {}
extension TVShowWrapper: HasPoster {}

struct PosterCard: View {
    let item: any HasPoster
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            AsyncImage(url: item.posterURL) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle()
                    .fill(Color.gray.opacity(0.3))
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundColor(.gray)
                    }
            }
            .frame(width: 120, height: 180)
            .cornerRadius(8)
            
            Text(item.title)
                .font(.caption)
                .lineLimit(2)
                .frame(width: 120)
        }
    }
}

