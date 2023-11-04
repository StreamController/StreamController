from itertools import groupby
import dbus
import sys

class MediaController:
    def __init__(self):
        self.session_bus = dbus.SessionBus()

    def update_players(self):
        mpris_players = []
        for i in self.session_bus.list_names():
            if str(i)[:22] == "org.mpris.MediaPlayer2":
                mpris_players += [self.session_bus.get_object(i, '/org/mpris/MediaPlayer2')]
        self.mpris_players = mpris_players

    def get_player_names(self, remove_duplicates = False):
        names = []
        for player in self.mpris_players:
            properties = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            name = properties.Get('org.mpris.MediaPlayer2', 'Identity')
            if remove_duplicates:
                if name in names:
                    continue
            names.append(str(name))
        return names
    
    def get_matching_ifaces(self, player_name: str = None) -> list[dbus.Interface]:
        self.update_players()
        """
        Retrieves a list of dbus interfaces that match the given player name.

        Args:
            player_name (str, optional): The name of the player to match. Defaults to None.
            If not provided, all interfaces will be returned.

        Returns:
            list[dbus.Interface]: A list of dbus interfaces that match the given player name.
        """
        ifaces = []
        for player in self.mpris_players:
            properties = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            if player_name in [None, "", properties.Get('org.mpris.MediaPlayer2', 'Identity')]:
                iface = dbus.Interface(player, 'org.mpris.MediaPlayer2.Player')
                ifaces.append(iface)
        return ifaces
    
    def pause(self, player_name: str = None):
        """
        Pauses the media player specified by the `player_name` parameter.

        Args:
            player_name (str, optional): The name of the media player to pause.
            If not provided, all media players will be paused.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.Pause()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)
        return self.compress_list(status)

    def play(self, player_name: str = None):
        """
        Plays the media player specified by the `player_name` parameter.

        Args:
            player_name (str, optional): The name of the media player to play.
            If not provided, all media players will be played.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.Play()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)
        return self.compress_list(status)
        
    def toggle(self, player_name: str = None):
        """
        Toggles the playback state of the media player specified by the `player_name` parameter.

        Args:
            player_name (str, optional): The name of the media player to toggle.
            If not provided, all media players will be toggled.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.PlayPause()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)
        return self.compress_list(status)
        
    def stop(self, player_name: str = None):
        """
        Stops the media player specified by the `player_name` parameter.

        Args:
            player_name (str, optional): The name of the media player to stop.
            If not provided, all media players will be stopped.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.Stop()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)
        return self.compress_list(status)

    def next(self, player_name: str = None):
        """
        Plays the next track for the media player specified by the `player_name` parameter.
        If `player_name` is not provided, it will play the next track for all media players.

        Args:
            player_name (str, optional): The name of the media player. Defaults to None.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.Next()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)

        return self.compress_list(status)

    def previous(self, player_name: str = None):
        """
        Plays the previous track for the media player specified by the `player_name` parameter.
        If `player_name` is not provided, it will play the previous track for all media players.

        Args:
            player_name (str, optional): The name of the media player. Defaults to None.

        Returns:
            None
        """
        status = []
        ifaces = self.get_matching_ifaces(player_name)
        for iface in ifaces:
            try:
                iface.Previous()
                status.append(True)
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(False)

        return self.compress_list(status)

    def status(self, player_name: str = None) -> list[bool]:
        ifaces = self.get_matching_ifaces(player_name)
        status = []
        for iface in ifaces:
            try:
                properties = dbus.Interface(iface, 'org.freedesktop.DBus.Properties')
                status.append(str(properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')))
            except dbus.exceptions.DBusException as e:
                print(e)
                status.append(None)

        return self.compress_list(status)
    
    def title(self, player_name: str = None) -> list[str]:
        ifaces = self.get_matching_ifaces(player_name)
        titles = []
        for iface in ifaces:
            try:
                properties = dbus.Interface(iface, 'org.freedesktop.DBus.Properties')
                metadata = properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                titles.append(str(metadata['xesam:title']))
            except dbus.exceptions.DBusException as e:
                print(e)
                titles.append(None)

        return self.compress_list(titles)
    
    def artist(self, player_name: str = None) -> list[str]:
        ifaces = self.get_matching_ifaces(player_name)
        titles = []
        for iface in ifaces:
            try:
                properties = dbus.Interface(iface, 'org.freedesktop.DBus.Properties')
                metadata = properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                titles.append(str(metadata['xesam:artist'][0]))
            except dbus.exceptions.DBusException as e:
                print(e)
                titles.append(None)

        return self.compress_list(titles)
    
    def thumbnail(self, player_name: str = None) -> list[str]:
        ifaces = self.get_matching_ifaces(player_name)
        thumbnails = []
        for iface in ifaces:
            try:
                properties = dbus.Interface(iface, 'org.freedesktop.DBus.Properties')
                metadata = properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                path = str(metadata['mpris:artUrl'])
                path = path.replace("file://", "")
                thumbnails.append(path)
            except (dbus.exceptions.DBusException, KeyError) as e:
                print(e)
                thumbnails.append(None)

        return self.compress_list(thumbnails)

    def compress_list(self, list) -> list | bool:
        def all_equal(iterable):
            g = groupby(iterable)
            return next(g, True) and not next(g, False)
        
        if len(list) == 0:
            return None
        
        if all_equal(list):
            return [list[0]]
        return list