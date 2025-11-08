//
//  ArcticMediaApp.swift
//  ArcticMedia
//
//  Created on 2024
//

import SwiftUI

@main
struct ArcticMediaApp: App {
    @StateObject private var authManager = AuthManager.shared
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
        }
    }
}

