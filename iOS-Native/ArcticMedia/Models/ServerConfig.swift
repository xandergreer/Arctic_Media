//
//  ServerConfig.swift
//  ArcticMedia
//

import Foundation

struct ServerConfig: Codable {
    let url: String
    var apiBase: String {
        return "\(url)/api"
    }
}

