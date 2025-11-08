//
//  MainTabView.swift
//  ArcticMedia
//

import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Label("Home", systemImage: "house.fill")
                }
            
            TVShowsView()
                .tabItem {
                    Label("TV Shows", systemImage: "tv.fill")
                }
            
            MoviesView()
                .tabItem {
                    Label("Movies", systemImage: "film.fill")
                }
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
    }
}

