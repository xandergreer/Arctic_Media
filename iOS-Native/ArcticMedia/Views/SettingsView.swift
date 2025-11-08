//
//  SettingsView.swift
//  ArcticMedia
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        NavigationView {
            List {
                Section {
                    if let user = authManager.currentUser {
                        HStack {
                            Text("Username")
                            Spacer()
                            Text(user.username)
                                .foregroundColor(.secondary)
                        }
                        
                        HStack {
                            Text("Server")
                            Spacer()
                            Text(authManager.serverURL ?? "Not set")
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                        }
                    }
                } header: {
                    Text("Account")
                }
                
                Section {
                    Button(role: .destructive) {
                        authManager.logout()
                    } label: {
                        Text("Logout")
                    }
                    
                    Button(role: .destructive) {
                        authManager.clearServer()
                    } label: {
                        Text("Change Server")
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

