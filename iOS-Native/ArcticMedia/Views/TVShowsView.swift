//
//  TVShowsView.swift
//  ArcticMedia
//

import SwiftUI

struct TVShowsView: View {
    @State private var shows: [TVShow] = []
    @State private var isLoading: Bool = true
    @State private var currentPage: Int = 1
    @State private var totalPages: Int = 1
    
    let columns = [
        GridItem(.adaptive(minimum: 120), spacing: 16)
    ]
    
    var body: some View {
        NavigationView {
            ScrollView {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding()
                } else {
                    LazyVGrid(columns: columns, spacing: 16) {
                        ForEach(shows) { show in
                            NavigationLink(destination: ShowDetailView(showId: show.id, show: show)) {
                                PosterCard(item: TVShowWrapper(show))
                            }
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("TV Shows")
            .task {
                await loadShows()
            }
        }
    }
    
    private func loadShows() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let response = try await APIService.shared.getTVShows(page: currentPage, pageSize: 60, sort: "recent")
            await MainActor.run {
                shows = response.items
                totalPages = response.total_pages
            }
        } catch {
            print("Error loading TV shows: \(error)")
        }
    }
}

struct ShowDetailView: View {
    let showId: String
    let show: TVShow
    @State private var seasons: [Season] = []
    @State private var isLoading: Bool = true
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Show header
                HStack(spacing: 16) {
                    AsyncImage(url: show.posterURL) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Rectangle()
                            .fill(Color.gray.opacity(0.3))
                    }
                    .frame(width: 120, height: 180)
                    .cornerRadius(8)
                    
                    VStack(alignment: .leading, spacing: 8) {
                        Text(show.title)
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        if let year = show.year {
                            Text("\(year)")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        
                        if let seasons = show.seasons {
                            Text("\(seasons) seasons")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                }
                .padding()
                
                // Seasons list
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding()
                } else {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Seasons")
                            .font(.headline)
                            .padding(.horizontal)
                        
                        ForEach(seasons) { season in
                            NavigationLink(destination: EpisodesView(showId: showId, season: season)) {
                                HStack {
                                    Text(season.title)
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                }
                                .padding()
                                .background(Color.gray.opacity(0.1))
                                .cornerRadius(8)
                            }
                            .padding(.horizontal)
                        }
                    }
                }
            }
        }
        .navigationTitle(show.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await loadSeasons()
        }
    }
    
    private func loadSeasons() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let loadedSeasons = try await APIService.shared.getSeasons(showId: showId)
            await MainActor.run {
                seasons = loadedSeasons
            }
        } catch {
            print("Error loading seasons: \(error)")
        }
    }
}

struct EpisodesView: View {
    let showId: String
    let season: Season
    @State private var episodes: [Episode] = []
    @State private var isLoading: Bool = true
    
    var body: some View {
        List {
            if isLoading {
                ProgressView()
            } else {
                ForEach(episodes) { episode in
                    NavigationLink(destination: PlayerView(episode: episode)) {
                        HStack {
                            AsyncImage(url: episode.stillURL) { image in
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            } placeholder: {
                                Rectangle()
                                    .fill(Color.gray.opacity(0.3))
                            }
                            .frame(width: 120, height: 68)
                            .cornerRadius(4)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text(episode.title)
                                    .font(.headline)
                                
                                if let episodeNum = episode.episode {
                                    Text("Episode \(episodeNum)")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(season.title)
        .task {
            await loadEpisodes()
        }
    }
    
    private func loadEpisodes() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let loadedEpisodes = try await APIService.shared.getEpisodes(showId: showId, season: season.season)
            await MainActor.run {
                episodes = loadedEpisodes
            }
        } catch {
            print("Error loading episodes: \(error)")
        }
    }
}

