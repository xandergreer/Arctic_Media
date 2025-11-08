//
//  User.swift
//  ArcticMedia
//

import Foundation

struct User: Codable, Identifiable {
    let id: String
    let email: String
    let username: String
    let role: String
    let created_at: String
}

