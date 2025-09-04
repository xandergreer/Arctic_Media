import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Image,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';

type HomeScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Home'>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { user, logout, serverConfig, clearServerConfig } = useAuthStore();

  const handleLogout = async () => {
    await logout();
  };

  const handleChangeServer = () => {
    clearServerConfig();
  };

  const navigateToTVShows = () => {
    navigation.navigate('TVShows');
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.welcomeText}>
            Welcome back, {user?.username || 'User'}!
          </Text>
          <Text style={styles.serverText}>
            Connected to: {serverConfig?.url}
          </Text>
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity style={styles.changeServerButton} onPress={handleChangeServer}>
            <Text style={styles.changeServerButtonText}>Change Server</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.content}>
        <Text style={styles.sectionTitle}>Your Media Library</Text>

        <View style={styles.menuGrid}>
          <TouchableOpacity style={styles.menuItem} onPress={navigateToTVShows}>
            <View style={styles.menuIcon}>
              <Text style={styles.menuIconText}>📺</Text>
            </View>
            <Text style={styles.menuItemTitle}>TV Shows</Text>
            <Text style={styles.menuItemSubtitle}>Browse your TV series</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIcon}>
              <Text style={styles.menuIconText}>🎬</Text>
            </View>
            <Text style={styles.menuItemTitle}>Movies</Text>
            <Text style={styles.menuItemSubtitle}>Watch your movies</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIcon}>
              <Text style={styles.menuIconText}>🎵</Text>
            </View>
            <Text style={styles.menuItemTitle}>Music</Text>
            <Text style={styles.menuItemSubtitle}>Listen to your music</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuIcon}>
              <Text style={styles.menuIconText}>📚</Text>
            </View>
            <Text style={styles.menuItemTitle}>Libraries</Text>
            <Text style={styles.menuItemSubtitle}>Manage your libraries</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.recentSection}>
          <Text style={styles.sectionTitle}>Recently Watched</Text>
          <Text style={styles.emptyText}>No recent activity</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  headerLeft: {
    flex: 1,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: 8,
  },
  welcomeText: {
    fontSize: 18,
    color: '#ffffff',
    fontWeight: '600',
    marginBottom: 4,
  },
  serverText: {
    fontSize: 12,
    color: '#999999',
    fontStyle: 'italic',
  },
  changeServerButton: {
    backgroundColor: '#5856D6',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  changeServerButtonText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  logoutButton: {
    backgroundColor: '#FF3B30',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  logoutButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  content: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 20,
  },
  menuGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 40,
  },
  menuItem: {
    width: '48%',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333333',
  },
  menuIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 15,
  },
  menuIconText: {
    fontSize: 30,
  },
  menuItemTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 8,
    textAlign: 'center',
  },
  menuItemSubtitle: {
    fontSize: 14,
    color: '#cccccc',
    textAlign: 'center',
  },
  recentSection: {
    marginTop: 20,
  },
  emptyText: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
});
