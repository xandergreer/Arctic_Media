import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';
import { mediaAPI } from '../api/media';
import { Library } from '../types';
import DrawerMenu from '../components/DrawerMenu';

type SettingsScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Settings'>;

export default function SettingsScreen() {
  const navigation = useNavigation<SettingsScreenNavigationProp>();
  const { user, logout, serverConfig, clearServerConfig } = useAuthStore();
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [loadingLibraries, setLoadingLibraries] = useState(false);
  const [selectedSection, setSelectedSection] = useState<'general' | 'libraries' | 'admin'>('general');

  useEffect(() => {
    if (selectedSection === 'libraries') {
      loadLibraries();
    }
  }, [selectedSection]);

  const loadLibraries = async () => {
    try {
      setLoadingLibraries(true);
      const libs = await mediaAPI.getLibraries();
      setLibraries(libs);
    } catch (error) {
      console.error('Failed to load libraries:', error);
    } finally {
      setLoadingLibraries(false);
    }
  };

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
          },
        },
      ]
    );
  };

  const handleChangeServer = () => {
    Alert.alert(
      'Change Server',
      'Are you sure you want to change server? This will log you out.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Change Server',
          style: 'destructive',
          onPress: () => {
            clearServerConfig();
          },
        },
      ]
    );
  };

  const isAdmin = user?.is_admin || false;

  return (
    <>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backButtonText}>‹ Back</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.menuButton}
            onPress={() => setDrawerVisible(true)}
          >
            <Text style={styles.menuButtonText}>☰</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.content}>
          <Text style={styles.title}>Settings</Text>

          {/* Section Tabs */}
          <View style={styles.tabs}>
            <TouchableOpacity
              style={[styles.tab, selectedSection === 'general' && styles.tabActive]}
              onPress={() => setSelectedSection('general')}
            >
              <Text style={[styles.tabText, selectedSection === 'general' && styles.tabTextActive]}>
                General
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, selectedSection === 'libraries' && styles.tabActive]}
              onPress={() => setSelectedSection('libraries')}
            >
              <Text style={[styles.tabText, selectedSection === 'libraries' && styles.tabTextActive]}>
                Libraries
              </Text>
            </TouchableOpacity>
            {isAdmin && (
              <TouchableOpacity
                style={[styles.tab, selectedSection === 'admin' && styles.tabActive]}
                onPress={() => setSelectedSection('admin')}
              >
                <Text style={[styles.tabText, selectedSection === 'admin' && styles.tabTextActive]}>
                  Admin
                </Text>
              </TouchableOpacity>
            )}
          </View>

          {/* General Section */}
          {selectedSection === 'general' && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Account</Text>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Username</Text>
                <Text style={styles.infoValue}>{user?.username || 'N/A'}</Text>
              </View>
              {user?.email && (
                <View style={styles.infoRow}>
                  <Text style={styles.infoLabel}>Email</Text>
                  <Text style={styles.infoValue}>{user.email}</Text>
                </View>
              )}
              {user?.is_admin && (
                <View style={styles.infoRow}>
                  <Text style={styles.infoLabel}>Role</Text>
                  <Text style={styles.infoValue}>Administrator</Text>
                </View>
              )}

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Server</Text>
                <View style={styles.infoRow}>
                  <Text style={styles.infoLabel}>Server URL</Text>
                  <Text style={styles.infoValue} numberOfLines={1}>
                    {serverConfig?.url || 'Not configured'}
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={handleChangeServer}
                >
                  <Text style={styles.actionButtonText}>Change Server</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Preferences</Text>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Auto-play videos</Text>
                    <Text style={styles.settingDescription}>Automatically start playing when opening a video</Text>
                  </View>
                  <Switch
                    value={true}
                    onValueChange={() => {}}
                    trackColor={{ false: '#333333', true: '#007AFF' }}
                  />
                </View>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Show thumbnails</Text>
                    <Text style={styles.settingDescription}>Display episode and season thumbnails</Text>
                  </View>
                  <Switch
                    value={true}
                    onValueChange={() => {}}
                    trackColor={{ false: '#333333', true: '#007AFF' }}
                  />
                </View>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Playback Settings</Text>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Default playback quality</Text>
                    <Text style={styles.settingDescription}>Preferred video quality for streaming</Text>
                  </View>
                  <View style={styles.pickerContainer}>
                    <Text style={styles.pickerText}>Auto</Text>
                  </View>
                </View>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Playback speed</Text>
                    <Text style={styles.settingDescription}>Default playback speed for videos</Text>
                  </View>
                  <View style={styles.pickerContainer}>
                    <Text style={styles.pickerText}>1.0x</Text>
                  </View>
                </View>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Auto-resume playback</Text>
                    <Text style={styles.settingDescription}>Continue from where you left off</Text>
                  </View>
                  <Switch
                    value={true}
                    onValueChange={() => {}}
                    trackColor={{ false: '#333333', true: '#007AFF' }}
                  />
                </View>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Subtitles enabled</Text>
                    <Text style={styles.settingDescription}>Show subtitles by default when available</Text>
                  </View>
                  <Switch
                    value={false}
                    onValueChange={() => {}}
                    trackColor={{ false: '#333333', true: '#007AFF' }}
                  />
                </View>
                <View style={styles.settingRow}>
                  <View style={styles.settingInfo}>
                    <Text style={styles.settingLabel}>Prefer HLS streaming</Text>
                    <Text style={styles.settingDescription}>Use HLS format for better mobile performance</Text>
                  </View>
                  <Switch
                    value={true}
                    onValueChange={() => {}}
                    trackColor={{ false: '#333333', true: '#007AFF' }}
                  />
                </View>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>About</Text>
                <Text style={styles.aboutText}>Arctic Media iOS App</Text>
                <Text style={styles.versionText}>Version 1.0.0</Text>
                <Text style={styles.aboutText}>
                  A modern media server client for iOS
                </Text>
              </View>
            </View>
          )}

          {/* Libraries Section */}
          {selectedSection === 'libraries' && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Libraries</Text>
              {loadingLibraries ? (
                <ActivityIndicator size="small" color="#007AFF" />
              ) : libraries.length > 0 ? (
                <View>
                  {libraries.map((lib) => (
                    <View key={lib.id} style={styles.libraryCard}>
                      <View style={styles.libraryInfo}>
                        <Text style={styles.libraryName}>{lib.name}</Text>
                        <Text style={styles.libraryType}>{lib.type.toUpperCase()}</Text>
                        <Text style={styles.libraryPath} numberOfLines={1}>{lib.path}</Text>
                      </View>
                      {isAdmin && (
                        <TouchableOpacity
                          style={styles.deleteButton}
                          onPress={() => {
                            Alert.alert(
                              'Delete Library',
                              `Are you sure you want to delete "${lib.name}"?`,
                              [
                                { text: 'Cancel', style: 'cancel' },
                                {
                                  text: 'Delete',
                                  style: 'destructive',
                                  onPress: async () => {
                                    // TODO: Implement delete library
                                    Alert.alert('Info', 'Library deletion not yet implemented in the app.');
                                  },
                                },
                              ]
                            );
                          }}
                        >
                          <Text style={styles.deleteButtonText}>Delete</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.emptyText}>No libraries found</Text>
              )}
              {isAdmin && (
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={() => {
                    Alert.alert('Info', 'Adding libraries is not yet available in the app. Please use the web interface.');
                  }}
                >
                  <Text style={styles.actionButtonText}>Add Library</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* Admin Section */}
          {selectedSection === 'admin' && isAdmin && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Admin Settings</Text>
              <Text style={styles.sectionDescription}>
                Advanced server configuration and management options
              </Text>

              <TouchableOpacity
                style={styles.adminCard}
                onPress={() => {
                  Alert.alert('Info', 'Transcoder settings are not yet available in the app. Please use the web interface.');
                }}
              >
                <Text style={styles.adminCardTitle}>Transcoder Settings</Text>
                <Text style={styles.adminCardDescription}>
                  Configure video transcoding options and quality settings
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.adminCard}
                onPress={() => {
                  Alert.alert('Info', 'Remote access settings are not yet available in the app. Please use the web interface.');
                }}
              >
                <Text style={styles.adminCardTitle}>Remote Access</Text>
                <Text style={styles.adminCardDescription}>
                  Configure remote access and public URL settings
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.adminCard}
                onPress={() => {
                  Alert.alert('Info', 'User management is not yet available in the app. Please use the web interface.');
                }}
              >
                <Text style={styles.adminCardTitle}>User Management</Text>
                <Text style={styles.adminCardDescription}>
                  Add, edit, and manage user accounts and permissions
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.adminCard}
                onPress={() => {
                  Alert.alert('Info', 'Scheduled tasks are not yet available in the app. Please use the web interface.');
                }}
              >
                <Text style={styles.adminCardTitle}>Scheduled Tasks</Text>
                <Text style={styles.adminCardDescription}>
                  View and manage scheduled background tasks
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.adminCard}
                onPress={() => {
                  Alert.alert('Info', 'Server configuration is not yet available in the app. Please use the web interface.');
                }}
              >
                <Text style={styles.adminCardTitle}>Server Configuration</Text>
                <Text style={styles.adminCardDescription}>
                  Configure server host, port, SSL, and other advanced settings
                </Text>
              </TouchableOpacity>
            </View>
          )}

          <TouchableOpacity
            style={styles.logoutButton}
            onPress={handleLogout}
          >
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <DrawerMenu visible={drawerVisible} onClose={() => setDrawerVisible(false)} />
    </>
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
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 20,
    paddingTop: 60,
  },
  backButton: {
    backgroundColor: '#333333',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  menuButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#333333',
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuButtonText: {
    color: '#ffffff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 24,
  },
  tabs: {
    flexDirection: 'row',
    marginBottom: 24,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    padding: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: '#007AFF',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#999999',
  },
  tabTextActive: {
    color: '#ffffff',
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 16,
  },
  sectionDescription: {
    fontSize: 14,
    color: '#999999',
    marginBottom: 20,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  infoLabel: {
    fontSize: 14,
    color: '#999999',
  },
  infoValue: {
    fontSize: 14,
    color: '#ffffff',
    flex: 1,
    textAlign: 'right',
    marginLeft: 16,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#ffffff',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 12,
    color: '#999999',
  },
  actionButton: {
    backgroundColor: '#333333',
    padding: 14,
    borderRadius: 8,
    marginTop: 12,
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  libraryCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  libraryInfo: {
    flex: 1,
  },
  libraryName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
  },
  libraryType: {
    fontSize: 12,
    color: '#007AFF',
    marginBottom: 4,
  },
  libraryPath: {
    fontSize: 12,
    color: '#999999',
  },
  deleteButton: {
    backgroundColor: '#FF3B30',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    marginLeft: 12,
  },
  deleteButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  adminCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333333',
  },
  adminCardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 6,
  },
  adminCardDescription: {
    fontSize: 13,
    color: '#999999',
    lineHeight: 18,
  },
  aboutText: {
    fontSize: 14,
    color: '#cccccc',
    marginBottom: 8,
  },
  versionText: {
    fontSize: 12,
    color: '#999999',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#666666',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 40,
  },
  pickerContainer: {
    backgroundColor: '#333333',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    minWidth: 80,
    alignItems: 'center',
  },
  pickerText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
  },
  logoutButton: {
    backgroundColor: '#FF3B30',
    padding: 16,
    borderRadius: 8,
    marginTop: 32,
    alignItems: 'center',
  },
  logoutButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
