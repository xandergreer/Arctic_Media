//
//  ContentView.swift
//  ArcticMedia
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        Group {
            if authManager.serverURL == nil {
                ServerConfigView()
            } else if !authManager.isAuthenticated {
                LoginView()
            } else {
                MainTabView()
            }
        }
    }
}

