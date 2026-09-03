import subprocess
import os
import time
import psutil


class ExternalApplicationManager:

    def __init__(self, settings):

        self.settings = settings
        self.applications = []

        for application in settings.get_external_applications():

            self.applications.append({
                "path": application.get("path", ""),
                "start_with_app": application.get(
                    "start_with_app",
                    True
                ),
                "stop_with_app": application.get(
                    "stop_with_app",
                    True
                ),
                "processes": [],
                "started_at": None
            })


    # --------------------------------------------------
    # ADD
    # --------------------------------------------------

    def add(
        self,
        path,
        start_with_app=True,
        stop_with_app=True
    ):

        application = {
            "path": path,
            "start_with_app": start_with_app,
            "stop_with_app": stop_with_app,
            "processes": [],
            "started_at": None
        }

        self.applications.append(application)

        return application


    # --------------------------------------------------
    # PROZESSE SNAPSHOT
    # --------------------------------------------------

    def _snapshot_processes(self):

        result = {}

        for process in psutil.process_iter(
            [
                "pid",
                "name",
                "exe",
                "create_time"
            ]
        ):

            try:

                info = process.info

                result[info["pid"]] = {
                    "name": info.get("name"),
                    "exe": info.get("exe"),
                    "create_time": info.get(
                        "create_time",
                        0
                    )
                }

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):

                continue

        return result


    # --------------------------------------------------
    # START
    # --------------------------------------------------

    def start(self, application):

        if not application:
            return False


        path = application.get("path", "")

        if not path:
            return False


        path = path.strip().strip('"').strip("'")
        path = os.path.normpath(path)


        print(
            "Starte externe Anwendung:",
            path
        )


        # ----------------------------------------------
        # Bereits bekannte Prozesse prüfen
        # ----------------------------------------------

        alive = []

        for pid in application.get(
            "processes",
            []
        ):

            try:

                process = psutil.Process(pid)

                if process.is_running():

                    alive.append(pid)

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):

                continue


        application["processes"] = alive


        if alive:

            print(
                "Anwendung läuft bereits:",
                alive
            )

            return True


        # ----------------------------------------------
        # Snapshot vor Start
        # ----------------------------------------------

        before = self._snapshot_processes()

        application["started_at"] = time.time()

        start_time = time.time()


        try:

            if path.lower().endswith(".lnk"):

                subprocess.Popen(
                    [
                        "cmd",
                        "/c",
                        "start",
                        "",
                        path
                    ],
                    shell=False
                )

            else:

                subprocess.Popen(
                    [path]
                )


        except Exception as e:

            print(
                "Fehler beim Starten:",
                repr(e)
            )

            return False


        # ----------------------------------------------
        # Neue Prozesse suchen
        # ----------------------------------------------

        found = []


        for _ in range(50):

            time.sleep(0.1)

            after = self._snapshot_processes()


            for pid, info in after.items():

                if pid in before:
                    continue


                # Prozess wurde nach unserem Start erzeugt
                if info["create_time"] < start_time:
                    continue


                found.append(pid)


            if found:
                break


        # Keine Duplikate
        found = list(
            dict.fromkeys(found)
        )


        application["processes"] = found


        print(
            "Erkannte neue Prozesse:",
            found
        )


        for pid in found:

            try:

                process = psutil.Process(pid)

                print(
                    "  PID:",
                    pid,
                    "| Name:",
                    process.name(),
                    "| EXE:",
                    process.exe()
                )

            except Exception:

                pass


        if not found:

            print(
                "Keine neue Prozessinstanz erkannt."
            )

            return False


        return True


    # --------------------------------------------------
    # STOP
    # --------------------------------------------------

    def stop(self, application):

        if not application:
            return False


        path = application.get(
            "path",
            ""
        )

        started_at = application.get(
            "started_at"
        )


        print(
            "Beende externe Anwendung:",
            path
        )


        processes = []


        # ----------------------------------------------
        # Bereits bekannte Prozesse
        # ----------------------------------------------

        for pid in application.get(
            "processes",
            []
        ):

            try:

                process = psutil.Process(pid)

                if process.is_running():

                    processes.append(
                        process
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):

                continue


        # ----------------------------------------------
        # Aktuell laufende Prozesse nachsuchen
        # ----------------------------------------------

        if started_at:

            target_path = os.path.normcase(
                os.path.normpath(path)
            )

            for process in psutil.process_iter(
                [
                    "pid",
                    "exe",
                    "create_time"
                ]
            ):

                try:

                    exe = process.info.get(
                        "exe"
                    )

                    create_time = process.info.get(
                        "create_time",
                        0
                    )


                    if not exe:
                        continue


                    normalized_exe = os.path.normcase(
                        os.path.normpath(exe)
                    )


                    if (
                        normalized_exe == target_path
                        and create_time >= started_at
                    ):

                        if process.pid not in [
                            p.pid for p in processes
                        ]:

                            print(
                                "Zusätzliche Instanz gefunden:",
                                process.pid
                            )

                            processes.append(
                                process
                            )


                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess
                ):

                    continue


        if not processes:

            print(
                "Keine der gestarteten "
                "Prozessinstanzen läuft noch."
            )

            return False


        # ----------------------------------------------
        # Kinder ebenfalls erfassen
        # ----------------------------------------------

        all_processes = {}

        for process in processes:

            all_processes[
                process.pid
            ] = process

            try:

                for child in process.children(
                    recursive=True
                ):

                    all_processes[
                        child.pid
                    ] = child

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):

                pass


        processes = list(
            all_processes.values()
        )


        # ----------------------------------------------
        # Beenden
        # ----------------------------------------------

        for process in processes:

            try:

                print(
                    "Terminate:",
                    process.pid,
                    process.name()
                )

                process.terminate()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):

                continue


        # ----------------------------------------------
        # Warten
        # ----------------------------------------------

        _, alive = psutil.wait_procs(
            processes,
            timeout=3
        )


        # ----------------------------------------------
        # Erzwingen
        # ----------------------------------------------

        for process in alive:

            try:

                print(
                    "Kill:",
                    process.pid,
                    process.name()
                )

                process.kill()

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):

                continue


        application["processes"] = []
        application["started_at"] = None


        print(
            "Externe Anwendung beendet:",
            path
        )

        return True


    # --------------------------------------------------
    # START ALL
    # --------------------------------------------------

    def start_all(self):

        print(
            "Externe Anwendungen:",
            self.applications
        )

        for application in self.applications:

            if application.get(
                "start_with_app",
                True
            ):

                self.start(
                    application
                )


    # --------------------------------------------------
    # STOP ALL
    # --------------------------------------------------

    def stop_all(self):

        for application in self.applications:

            if application.get(
                "stop_with_app",
                True
            ):

                self.stop(
                    application
                )