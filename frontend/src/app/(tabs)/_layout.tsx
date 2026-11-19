import { Tabs } from 'expo-router';
import { View } from 'react-native';

import { colors } from '@/lib/theme';

function TabDot({ focused }: { focused: boolean }) {
  return <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: focused ? colors.primary : 'transparent' }} />;
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.text,
        tabBarIcon: ({ focused }) => <TabDot focused={focused} />,
        tabBarLabelStyle: { fontSize: 13, fontWeight: '500' },
        tabBarStyle: { backgroundColor: '#fff', borderTopColor: colors.border, height: 72, paddingTop: 6 },
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="drills" options={{ title: 'Drills' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
      <Tabs.Screen name="partners" options={{ title: 'Partners' }} />
    </Tabs>
  );
}
