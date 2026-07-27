import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";

import { AuthContext } from "./src/AuthContext";
import { api } from "./src/api";
import { theme } from "./src/theme";

import LoginScreen from "./src/screens/LoginScreen";
import RegisterScreen from "./src/screens/RegisterScreen";
import HomeScreen from "./src/screens/HomeScreen";
import ResultsScreen from "./src/screens/ResultsScreen";
import ProductScreen from "./src/screens/ProductScreen";
import BookingScreen from "./src/screens/BookingScreen";
import FeedbackScreen from "./src/screens/FeedbackScreen";
import BookingsScreen from "./src/screens/BookingsScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const stackOpts = {
  headerStyle: { backgroundColor: "#fff" },
  headerTintColor: theme.pink,
  headerTitleStyle: { color: theme.ink, fontWeight: "700" },
  headerTitleAlign: "center",
  headerShadowVisible: false,
};

// detail screens shared by tabs
function detailScreens() {
  return (
    <>
      <Stack.Screen name="Results" component={ResultsScreen} options={{ title: "Search Results" }} />
      <Stack.Screen name="Product" component={ProductScreen} options={{ title: "Product Details" }} />
      <Stack.Screen name="Booking" component={BookingScreen} options={{ title: "Book Dress" }} />
      <Stack.Screen name="Feedback" component={FeedbackScreen} options={{ title: "Give Feedback" }} />
    </>
  );
}

function HomeStack() {
  return (
    <Stack.Navigator screenOptions={stackOpts}>
      <Stack.Screen name="HomeMain" component={HomeScreen} options={{ headerShown: false }} />
      {detailScreens()}
    </Stack.Navigator>
  );
}

function BookingsStack() {
  return (
    <Stack.Navigator screenOptions={stackOpts}>
      <Stack.Screen name="BookingsMain" component={BookingsScreen} options={{ headerShown: false }} />
      {detailScreens()}
    </Stack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.pink,
        tabBarInactiveTintColor: theme.muted,
        tabBarStyle: { height: 60, paddingBottom: 8, paddingTop: 6, borderTopColor: theme.line },
        tabBarLabelStyle: { fontSize: 11 },
        tabBarIcon: ({ color, size }) => {
          const icons = { HomeTab: "home", BookingsTab: "calendar", ProfileTab: "person" };
          return <Ionicons name={icons[route.name]} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="HomeTab" component={HomeStack} options={{ title: "Home" }} />
      <Tab.Screen name="BookingsTab" component={BookingsStack} options={{ title: "Bookings" }} />
      <Tab.Screen name="ProfileTab" component={ProfileScreen} options={{ title: "Profile" }} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [name, setName] = useState("");

  useEffect(() => {
    api.restore().then((s) => {
      if (s) { setAuthed(true); setName(s.name || ""); }
      setReady(true);
    });
  }, []);

  const auth = {
    name,
    signIn: (nm) => { setName(nm || ""); setAuthed(true); },
    signOut: async () => { await api.logout(); setAuthed(false); },
  };

  if (!ready) {
    return (
      <View style={{ flex: 1, justifyContent: "center", backgroundColor: theme.pinkTint }}>
        <ActivityIndicator size="large" color={theme.pink} />
      </View>
    );
  }

  return (
    <AuthContext.Provider value={auth}>
      <StatusBar style="dark" />
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {!authed ? (
            <>
              <Stack.Screen name="Login" component={LoginScreen} />
              <Stack.Screen name="Register" component={RegisterScreen} />
            </>
          ) : (
            <Stack.Screen name="Main" component={MainTabs} />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </AuthContext.Provider>
  );
}
