//
//  MoviesView.swift
//  ArcticMedia
//

import SwiftUI

struct MoviesView: View {
    @State private var movies: [MediaItem] = []
    @State private var isLoading: Bool = true
    
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
                        ForEach(movies) { movie in
                            NavigationLink(destination: MovieDetailView(movie: movie)) {
                                PosterCard(item: MediaItemWrapper(movie))
                            }
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Movies")
            .task {
                await loadMovies()
            }
        }
    }
    
    private func loadMovies() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let response = try await APIService.shared.getMovies(page: 1, pageSize: 60, sort: "recent")
            await MainActor.run {
                movies = response.items
            }
        } catch {
            print("Error loading movies: \(error)")
        }
    }
}

struct MovieDetailView: View {
    let movie: MediaItem
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack(spacing: 16) {
                    AsyncImage(url: movie.posterURL) { image in
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
                        Text(movie.title)
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        if let year = movie.year {
                            Text("\(year)")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        
                        if let runtime = movie.runtime_ms {
                            let minutes = runtime / 60000
                            Text("\(minutes) min")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                }
                .padding()
                
                if let overview = movie.overview {
                    Text(overview)
                        .padding(.horizontal)
                }
                
                NavigationLink(destination: PlayerView(itemId: movie.id, title: movie.title)) {
                    HStack {
                        Image(systemName: "play.fill")
                        Text("Play")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(8)
                }
                .padding()
            }
        }
        .navigationTitle(movie.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

