import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

console.log("Three.js Version:", THREE.REVISION);


// ============================================================
// GRUNDSETUP
// ============================================================

const sceneContainer =
    document.getElementById("scene");

const addTrussButton = document.getElementById("addTruss");

const scene =
    new THREE.Scene();

scene.background =
    new THREE.Color(0x101010);

let projectChanged = false;


// ============================================================
// KAMERA
// ============================================================

const camera =
    new THREE.PerspectiveCamera(

        50,

        sceneContainer.clientWidth /
        sceneContainer.clientHeight,

        0.1,

        1000
    );

camera.position.set(
    8,
    7,
    10
);


// ============================================================
// WARNUNG BEIM SCHLIESSEN
// ============================================================

window.addEventListener(
    "beforeunload",
    event => {

        if (!projectChanged) {
            return;
        }

        event.preventDefault();

        event.returnValue = "";

    }
);


// ============================================================
// MOBILE / TABLET WARNUNG
// ============================================================

const isMobile =
    /Android|iPhone|iPad|iPod|Windows Phone/i.test(navigator.userAgent) ||
    window.innerWidth < 1200;

if (isMobile) {

    const warning =
        document.getElementById("desktopWarning");

    if (warning) {
        warning.style.display = "flex";
    }
}


// ============================================================
// RENDERER
// ============================================================

const renderer =
    new THREE.WebGLRenderer({

        antialias: true

    });

renderer.setPixelRatio(
    window.devicePixelRatio
);

renderer.setSize(

    sceneContainer.clientWidth,

    sceneContainer.clientHeight

);

renderer.shadowMap.enabled = true;

sceneContainer.appendChild(
    renderer.domElement
);


// ============================================================
// ORBIT CONTROLS
// ============================================================

const controls =
    new OrbitControls(
        camera,
        renderer.domElement
    );

controls.target.set(
    0,
    1,
    0
);

controls.enableDamping = true;


// ============================================================
// TRANSFORM CONTROLS
// ============================================================

const transformControls =
    new TransformControls(
        camera,
        renderer.domElement
    );

transformControls.setMode("translate");
transformControls.setSpace("world");
transformControls.setSize(0.9);

// Positions-Snap: 10 cm
const POSITION_SNAP = 0.1;

// Rotations-Snap: 45 Grad
const ROTATION_SNAP =
    THREE.MathUtils.degToRad(45);

transformControls.setTranslationSnap(
    POSITION_SNAP
);

transformControls.setRotationSnap(
    ROTATION_SNAP
);

scene.add(
    transformControls.getHelper()
);


// ============================================================
// TRANSFORM / ORBIT ZUSAMMENARBEIT
// ============================================================

transformControls.addEventListener(
    "dragging-changed",
    event => {

        controls.enabled =
            !event.value;


        if (event.value) {

            beginUndoAction();

        } else {

            endUndoAction();

        }

    }
);


// ============================================================
// GRUNDBELEUCHTUNG
// ============================================================

const ambientLight =
    new THREE.AmbientLight(
        0xffffff,
        0
    );

scene.add(
    ambientLight
);


const roomLight =
    new THREE.DirectionalLight(
        0xffffff,
        0.3
    );

roomLight.position.set(
    5,
    10,
    5
);

roomLight.castShadow = true;

scene.add(
    roomLight
);


// ============================================================
// UNIVERSUM
// ============================================================

let universeSize = 30;


// ============================================================
// BODEN
// ============================================================

const floorMaterial =
    new THREE.MeshStandardMaterial({

        color: 0x292929,

        roughness: 0.8

    });


const floor =
    new THREE.Mesh(

        new THREE.PlaneGeometry(
            universeSize,
            universeSize
        ),

        floorMaterial

    );

floor.rotation.x =
    -Math.PI / 2;

floor.receiveShadow = true;

scene.add(
    floor
);


// ============================================================
// RASTER
// ============================================================

let grid =
    new THREE.GridHelper(

        universeSize,

        universeSize,

        0x555555,

        0x333333

    );

grid.position.y =
    0.01;

scene.add(
    grid
);


// ============================================================
// UNIVERSUM GRÖSSE ÄNDERN
// ============================================================

function updateUniverseSize(
    size
) {

    universeSize =
        size;


    // ----------------------------------------
    // Boden
    // ----------------------------------------

    floor.geometry.dispose();

    floor.geometry =
        new THREE.PlaneGeometry(
            universeSize,
            universeSize
        );


    // ----------------------------------------
    // Raster
    // ----------------------------------------

    scene.remove(
        grid
    );

    grid.geometry.dispose();

    if (Array.isArray(grid.material)) {

        grid.material.forEach(
            material => material.dispose()
        );

    } else {

        grid.material.dispose();

    }


    grid =
        new THREE.GridHelper(

            universeSize,

            Math.round(universeSize),

            0x555555,

            0x333333

        );

    grid.position.y =
        0.01;

    scene.add(
        grid
    );
}


// ============================================================
// ACHSEN
// ============================================================

const axes =
    new THREE.AxesHelper(2);

scene.add(
    axes
);


// ============================================================
// FIXTURE STORAGE
// ============================================================

let fixtures = [];

let selectedFixture = null;

let fixtureCounter = 0;

let copiedSettings = null;

// Zusätzliche Bühnenobjekte
let stageObjects = [];

let selectedStageObject = null;

let stageObjectCounter = 0;

let trusses = [];

let trussCounter = 0;

let selectedTruss = null;

// ============================================================
// UNDO / REDO
// ============================================================

let undoStack = [];

let redoStack = [];

const MAX_UNDO_STEPS = 50;

let historyActionOpen = false;


// ============================================================
// POSITIONS-INPUTS
// ============================================================

const xInput =
    document.getElementById("xInput");

const yInput =
    document.getElementById("yInput");

const zInput =
    document.getElementById("zInput");


// ============================================================
// GLOBAL BEAM
// ============================================================

let globalBeamLength = 5;

let globalBeamsVisible = true;


function getDeviceDefinition(deviceId) {

    return availableDevices.find(

        device =>
            Number(device.id) ===
            Number(deviceId)

    ) || null;
}


// ============================================================
// DMX DEVICE HINZUFÜGEN
// ============================================================

document.getElementById(
    "addDevice"
).addEventListener(

    "click",

    () => {

        if (!selectedFixture) {

            alert(
                "Please select a Moving Head first."
            );

            return;

        }


        const select =
            document.getElementById(
                "deviceSelect"
            );


        const deviceId =
            parseInt(
                select.value
            );


        if (Number.isNaN(deviceId)) {

            alert(
                "Please select a Device."
            );

            return;

        }


        const definition =
            getDeviceDefinition(
                deviceId
            );


        if (!definition) {

            return;

        }


        beginUndoAction();


        const channels = {};


        for (
            let i = 1;
            i <= definition.channels;
            i++
        ) {

            channels[i] =
                0;

        }


        selectedFixture.devices.push({

            device_id:
                definition.id,

            start_channel:
                definition.start_channel ?? 1,

            channels:
                channels

        });


        renderDeviceAssignments();

        markProjectChanged();

        endUndoAction();


        select.value = "";
    }

);



// ============================================================
// DMX DEVICES ANZEIGEN
// ============================================================

function renderDeviceAssignments() {

    const container =
        document.getElementById(
            "deviceAssignments"
        );


    container.innerHTML = "";


    if (!selectedFixture) {
        return;
    }


    selectedFixture.devices.forEach(

        (assignment, deviceIndex) => {

            const definition =
                getDeviceDefinition(
                    assignment.device_id
                );


            if (!definition) {
                return;
            }


            const wrapper =
                document.createElement(
                    "div"
                );


            wrapper.className =
                "device-assignment";


            // ----------------------------------------
            // HEADER
            // ----------------------------------------

            const header =
                document.createElement(
                    "div"
                );


            header.className =
                "device-header";


            const title =
                document.createElement(
                    "strong"
                );


            title.textContent =
                definition.name;


            const removeButton =
                document.createElement(
                    "button"
                );


            removeButton.textContent =
                "×";


            removeButton.addEventListener(
                "click",
                () => {

                    beginUndoAction();


                    selectedFixture.devices.splice(
                        deviceIndex,
                        1
                    );


                    renderDeviceAssignments();

                    markProjectChanged();

                    endUndoAction();

                }
            );


            header.appendChild(
                title
            );

            header.appendChild(
                removeButton
            );

            wrapper.appendChild(
                header
            );


            // ----------------------------------------
            // START CHANNEL
            // ----------------------------------------

            const startLabel =
                document.createElement(
                    "label"
                );


            startLabel.textContent =
                "Start Channel";


            const startInput =
                document.createElement(
                    "input"
                );


            startInput.type =
                "number";

            startInput.min =
                "1";

            startInput.max =
                "512";

            startInput.value =
                assignment.start_channel;


            startInput.className =
                "device-start-channel";


            startInput.addEventListener(
                "focus",
                () => {
                    beginUndoAction();
                }
            );


            startInput.addEventListener(
                "blur",
                () => {
                    endUndoAction();
                }
            );


            startInput.addEventListener(
                "input",
                () => {

                    let value =
                        parseInt(
                            startInput.value
                        );


                    if (
                        Number.isNaN(value)
                    ) {

                        return;

                    }


                    value =
                        Math.max(
                            1,
                            Math.min(
                                512,
                                value
                            )
                        );


                    assignment.start_channel =
                        value;


                    markProjectChanged();

                }
            );


            wrapper.appendChild(
                startLabel
            );

            wrapper.appendChild(
                startInput
            );


            // ----------------------------------------
            // CHANNELS
            // ----------------------------------------

            const channelsContainer =
                document.createElement(
                    "div"
                );


            channelsContainer.className =
                "device-channels";


            for (
                let channel = 1;
                channel <= definition.channels;
                channel++
            ) {

                if (
                    assignment.channels[channel] ===
                    undefined
                ) {

                    assignment.channels[channel] =
                        0;

                }


                const row =
                    document.createElement(
                        "div"
                    );


                row.className =
                    "device-channel";


                const number =
                    document.createElement(
                        "span"
                    );


                number.className =
                    "device-channel-number";


                number.textContent =
                    channel;


                const name =
                    document.createElement(
                        "span"
                    );


                name.className =
                    "device-channel-name";


                name.textContent =
                    definition.channel_names?.[
                        channel - 1
                    ] ||
                    `Channel ${channel}`;


                const input =
                    document.createElement(
                        "input"
                    );


                input.type =
                    "number";

                input.min =
                    "0";

                input.max =
                    "255";

                input.value =
                    assignment.channels[channel];


                input.addEventListener(
                    "focus",
                    () => {
                        beginUndoAction();
                    }
                );


                input.addEventListener(
                    "blur",
                    () => {
                        endUndoAction();
                    }
                );


                input.addEventListener(
                    "input",
                    () => {

                        let value =
                            parseInt(
                                input.value
                            );


                        if (
                            Number.isNaN(value)
                        ) {

                            return;

                        }


                        value =
                            Math.max(
                                0,
                                Math.min(
                                    255,
                                    value
                                )
                            );


                        assignment.channels[channel] =
                            value;


                        markProjectChanged();

                    }
                );


                row.appendChild(
                    number
                );

                row.appendChild(
                    name
                );

                row.appendChild(
                    input
                );


                channelsContainer.appendChild(
                    row
                );

            }


            wrapper.appendChild(
                channelsContainer
            );


            container.appendChild(
                wrapper
            );

        }
    );
}


// ============================================================
// MOVING HEAD KLASSE
// ============================================================

class MovingHead {

    constructor(
        id,
        position = new THREE.Vector3()
    ) {

        this.id = id;
        this.devices = [];


        // ----------------------------------------
        // HAUPTGRUPPE
        // ----------------------------------------

        this.group =
            new THREE.Group();

        this.group.position.copy(
            position
        );

        scene.add(
            this.group
        );


        // ----------------------------------------
        // BASIS
        // ----------------------------------------

        const baseGeometry =
            new THREE.CylinderGeometry(

                0.14,
                0.14,
                0.14,
                24

            );


        const baseMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x202020,

                metalness: 0.7,

                roughness: 0.35

            });


        this.base =
            new THREE.Mesh(

                baseGeometry,

                baseMaterial

            );

        this.base.position.y =
            0.05;

        this.base.castShadow =
            true;

        this.group.add(
            this.base
        );


        // ----------------------------------------
        // PAN
        // ----------------------------------------

        this.panGroup =
            new THREE.Group();

        this.panGroup.position.y =
            0.10;

        this.group.add(
            this.panGroup
        );


        // ----------------------------------------
        // BÜGEL
        // ----------------------------------------

        const yokeGeometry =
            new THREE.BoxGeometry(

                0.045,
                0.35,
                0.045

            );


        const yokeMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x333333,

                metalness: 0.7

            });


        const yokeLeft =
            new THREE.Mesh(

                yokeGeometry,

                yokeMaterial

            );

        yokeLeft.position.set(
            -0.12,
            0.15,
            0
        );

        this.panGroup.add(
            yokeLeft
        );


        const yokeRight =
            new THREE.Mesh(

                yokeGeometry,

                yokeMaterial

            );

        yokeRight.position.set(
            0.12,
            0.15,
            0
        );

        this.panGroup.add(
            yokeRight
        );


        // ----------------------------------------
        // TILT
        // ----------------------------------------

        this.tiltGroup =
            new THREE.Group();

        this.tiltGroup.position.y =
            0.32;

        this.panGroup.add(
            this.tiltGroup
        );


        // ----------------------------------------
        // KOPF
        // ----------------------------------------

        const headGeometry =
            new THREE.BoxGeometry(
                0.20,
                0.20,
                0.30
            );


        const headMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x444444,

                metalness: 0.65,

                roughness: 0.3

            });


        this.head =
            new THREE.Mesh(

                headGeometry,

                headMaterial

            );

        this.head.castShadow =
            true;

        this.tiltGroup.add(
            this.head
        );


        // ----------------------------------------
        // LINSE
        // ----------------------------------------

        const lensGeometry =
            new THREE.CircleGeometry(
                0.085,
                32
            );


        this.lensMaterial =
            new THREE.MeshBasicMaterial({

                color: 0xffffff,

                side: THREE.DoubleSide

            });


        this.lens =
            new THREE.Mesh(

                lensGeometry,

                this.lensMaterial

            );


        this.lens.position.z =
            0.155;


        this.lens.rotation.y =
            0;


        this.tiltGroup.add(
            this.lens
        );


        // ----------------------------------------
        // ECHTES THREE.JS LICHT
        // ----------------------------------------

        this.light =
            new THREE.SpotLight(

                0xffffff,

                5,

                globalBeamLength,

                THREE.MathUtils.degToRad(20),

                0.45,

                1

            );


        this.light.castShadow =
            true;


        this.light.position.set(

            0,
            0,
            0.15

        );


        this.tiltGroup.add(
            this.light
        );


        // ----------------------------------------
        // LICHTZIEL
        // ----------------------------------------

        this.lightTarget =
            new THREE.Object3D();


        this.lightTarget.position.set(

            0,
            0,
            globalBeamLength

        );


        this.tiltGroup.add(
            this.lightTarget
        );


        this.light.target =
            this.lightTarget;


        // ----------------------------------------
        // SICHTBARER BEAM
        // ----------------------------------------

        this.beam =
            this.createBeam();


        this.tiltGroup.add(
            this.beam
        );


        // ----------------------------------------
        // STANDARDWERTE
        // ----------------------------------------

        this.pan =
            0;

        this.tilt =
            0;

        this.color =
            "#ffffff";

        this.intensity =
            5;

        this.angle =
            20;


        this.update();
    }


    // ========================================================
    // BEAM ERSTELLEN
    // ========================================================

    createBeam() {

        const geometry =
            new THREE.ConeGeometry(

                1,
                1,
                48,
                1,
                true

            );


        const material =
            new THREE.MeshBasicMaterial({

                color: 0xffffff,

                transparent: true,

                opacity: 0.12,

                depthWrite: false,

                side: THREE.DoubleSide,

                blending:
                    THREE.AdditiveBlending

            });


        const beam =
            new THREE.Mesh(

                geometry,

                material

            );


        beam.rotation.x =
            -Math.PI / 2;


        return beam;
    }


    // ========================================================
    // UPDATE
    // ========================================================

    update() {

        // ----------------------------------------
        // PAN
        // ----------------------------------------

        this.panGroup.rotation.y =
            THREE.MathUtils.degToRad(
                this.pan
            );


        // ----------------------------------------
        // TILT - REVERSED
        // ----------------------------------------

        this.tiltGroup.rotation.x =
            -THREE.MathUtils.degToRad(
                this.tilt
            );


        // ----------------------------------------
        // FARBE
        // ----------------------------------------

        const color =
            new THREE.Color(
                this.color
            );


        this.light.color.copy(
            color
        );


        this.lensMaterial.color.copy(
            color
        );


        this.beam.material.color.copy(
            color
        );


        // ----------------------------------------
        // INTENSITÄT
        // ----------------------------------------

        this.light.intensity =
            this.intensity;


        // ----------------------------------------
        // BEAM ANGLE
        // ----------------------------------------

        this.light.angle =
            THREE.MathUtils.degToRad(
                this.angle
            );


        
        // ----------------------------------------
        // BEAM AN DER GRUNDPLATTE BEGRENZEN
        // ----------------------------------------

        const maxBeamLength = globalBeamLength;
        const floorY = 0;

        // Position und Richtung der Lichtquelle in Weltkoordinaten
        this.tiltGroup.updateWorldMatrix(true, false);

        const origin = new THREE.Vector3(0, 0, 0.15);
        this.tiltGroup.localToWorld(origin);

        const direction = new THREE.Vector3(0, 0, 1)
            .transformDirection(this.tiltGroup.matrixWorld);

        let beamLength = maxBeamLength;

        // Nur begrenzen, wenn der Strahl nach unten zeigt
        if (direction.y < -0.0001) {
            const distanceToFloor =
                (floorY - origin.y) / direction.y;

            if (distanceToFloor >= 0) {
                beamLength = Math.min(
                    maxBeamLength,
                    distanceToFloor
                );
            }
        }

        beamLength = Math.max(0, beamLength);

        // ----------------------------------------
        // ECHTES THREE.JS LICHT
        // ----------------------------------------

        this.light.distance = beamLength;
        this.light.position.set(0, 0, 0.15);


        // ----------------------------------------
        // SICHTBARKEIT
        // ----------------------------------------

        this.beam.visible =
            globalBeamsVisible && beamLength > 0;

        // ----------------------------------------
        // BEAM RADIUS
        // ----------------------------------------

        const radius = Math.tan(
            THREE.MathUtils.degToRad(this.angle / 2)
        ) * beamLength;

        // ----------------------------------------
        // BEAM SKALIEREN
        // ----------------------------------------

        this.beam.scale.set(
            radius,
            beamLength,
            radius
        );

        // ----------------------------------------
        // BEAM POSITION
        // ----------------------------------------

        this.beam.position.set(
            0,
            0,
            beamLength / 2
        );

        // ----------------------------------------
        // LICHTZIEL
        // ----------------------------------------

        this.lightTarget.position.set(
            0,
            0,
            beamLength
        );
    }


    // ========================================================
    // AUSWAHL
    // ========================================================

    setSelected(
        selected
    ) {

        if (selected) {

            this.base.material.emissive =
                new THREE.Color(
                    0x222222
                );

        } else {

            this.base.material.emissive =
                new THREE.Color(
                    0x000000
                );
        }
    }


    // ========================================================
    // LÖSCHEN
    // ========================================================

    remove() {

        if (
            selectedFixture === this
        ) {

            transformControls.detach();

        }


        scene.remove(
            this.group
        );


        this.group.traverse(
            object => {

                if (object.geometry) {

                    object.geometry.dispose();

                }


                if (object.material) {

                    if (
                        Array.isArray(
                            object.material
                        )
                    ) {

                        object.material.forEach(
                            material => {

                                material.dispose();

                            }
                        );

                    } else {

                        object.material.dispose();

                    }
                }
            }
        );
    }
}




class Truss {
    constructor(position = new THREE.Vector3(), length = 2) {
        this.id = `TR${++trussCounter}`;
        this.length = length;

        this.group = new THREE.Group();
        this.group.position.copy(position);

        this.material = new THREE.MeshStandardMaterial({
            color: 0xFFCBE8FF,
            metalness: 0.75,
            roughness: 0.3
        });

        this.barsGroup = new THREE.Group();
        this.group.add(this.barsGroup);

        // Unsichtbarer Endpunkt für den Längengriff
        this.endHandle = new THREE.Object3D();
        this.group.add(this.endHandle);

        this.rebuild();
        scene.add(this.group);
    }

    rebuild() {
        // Nur die Streben entfernen, nicht den Endpunkt
        while (this.barsGroup.children.length > 0) {
            const bar = this.barsGroup.children[0];
            this.barsGroup.remove(bar);

            bar.geometry.dispose();
        }

        const offset = 0.12;
        const radius = 0.025;

        const addBar = (start, end) => {
            const direction = new THREE.Vector3().subVectors(end, start);

            const geometry = new THREE.CylinderGeometry(
                radius,
                radius,
                direction.length(),
                8
            );

            const bar = new THREE.Mesh(geometry, this.material);

            bar.position.copy(start).add(end).multiplyScalar(0.5);
            bar.quaternion.setFromUnitVectors(
                new THREE.Vector3(0, 1, 0),
                direction.clone().normalize()
            );

            this.barsGroup.add(bar);
        };

        // Vier Längsstreben
        for (const y of [-offset, offset]) {
            for (const z of [-offset, offset]) {
                addBar(
                    new THREE.Vector3(0, y, z),
                    new THREE.Vector3(this.length, y, z)
                );
            }
        }

        
        // Diagonalstreben auf allen vier Wänden
        const sectionLength = 0.5;

        for (let x = 0; x < this.length - 0.001; x += sectionLength) {
            const nextX = Math.min(x + sectionLength, this.length);

            // Seitenwände: vorne und hinten (Y/Z-Ebene)
            for (const y of [-offset, offset]) {
                addBar(
                    new THREE.Vector3(x, y, -offset),
                    new THREE.Vector3(nextX, y, offset)
                );

                addBar(
                    new THREE.Vector3(x, y, offset),
                    new THREE.Vector3(nextX, y, -offset)
                );
            }

            // Ober- und Unterseite (X/Y-Ebene)
            for (const z of [-offset, offset]) {
                addBar(
                    new THREE.Vector3(x, -offset, z),
                    new THREE.Vector3(nextX, offset, z)
                );

                addBar(
                    new THREE.Vector3(x, offset, z),
                    new THREE.Vector3(nextX, -offset, z)
                );
            }
        }


        this.endHandle.position.set(this.length, 0, 0);
    }

    setLength(length) {
        const snappedLength = Math.max(
            0.5,
            Math.round(length / 0.5) * 0.5
        );

        if (snappedLength === this.length) return;

        this.length = snappedLength;
        this.rebuild();
    }

    remove() {
        scene.remove(this.group);

        this.group.traverse(object => {
            if (object.geometry) object.geometry.dispose();
        });

        this.material.dispose();
    }
}



// ============================================================
// HISTORY SNAPSHOT ERSTELLEN
// ============================================================

function createHistorySnapshot() {

    return {

        project:
            JSON.parse(
                JSON.stringify(
                    getProjectData()
                )
            ),

        selectedId:
            selectedFixture
                ? selectedFixture.id
                : null

    };
}


// ============================================================
// NEUE UNDO-AKTION BEGINNEN
// ============================================================

function beginUndoAction() {

    if (historyActionOpen) {
        return;
    }


    undoStack.push(
        createHistorySnapshot()
    );


    if (
        undoStack.length >
        MAX_UNDO_STEPS
    ) {

        undoStack.shift();

    }


    // Neue Änderung beendet REDO-Historie

    redoStack = [];


    historyActionOpen =
        true;
}


// ============================================================
// AKTION BEENDEN
// ============================================================

function endUndoAction() {

    historyActionOpen =
        false;
}


// ============================================================
// POSITION INPUTS LEEREN
// ============================================================

function clearPositionInputs() {

    if (xInput) {
        xInput.value = "";
    }

    if (yInput) {
        yInput.value = "";
    }

    if (zInput) {
        zInput.value = "";
    }
}


// ============================================================
// PROJEKT-ZUSTAND WIEDERHERSTELLEN
// ============================================================

function restoreHistorySnapshot(
    snapshot
) {

    const state =
        snapshot.project;


    // ----------------------------------------
    // ALLE AKTUELLEN FIXTURES ENTFERNEN
    // ----------------------------------------

    transformControls.detach();

    selectedFixture =
        null;


    fixtures.forEach(
        fixture => {

            fixture.remove();

        }
    );


    fixtures = [];

    fixtureCounter = 0;


    // ----------------------------------------
    // UNIVERSUM
    // ----------------------------------------

    universeSize =
        state.universeSize;


    updateUniverseSize(
        universeSize
    );


    document.getElementById(
        "universeSize"
    ).value =
        universeSize;


    document.getElementById(
        "universeSizeValue"
    ).textContent =
        `${universeSize} m`;


    // ----------------------------------------
    // GLOBALER BEAM
    // ----------------------------------------

    globalBeamLength =
        state.globalBeamLength;


    document.getElementById(
        "globalBeamLength"
    ).value =
        globalBeamLength;


    document.getElementById(
        "globalBeamLengthValue"
    ).textContent =
        `${globalBeamLength} m`;


    // ----------------------------------------
    // BEAM SICHTBARKEIT
    // ----------------------------------------

    globalBeamsVisible =
        state.globalBeamsVisible;


    document.getElementById(
        "globalBeamToggle"
    ).textContent =
        globalBeamsVisible
            ? "Beam ON"
            : "Beam OFF";


    // ----------------------------------------
    // FIXTURES
    // ----------------------------------------

    state.fixtures.forEach(
        data => {

            const fixture =
                new MovingHead(

                    data.id,

                    new THREE.Vector3(

                        data.position?.x ?? 0,

                        data.position?.y ?? 0,

                        data.position?.z ?? 0

                    )

                );


            fixture.id =
                data.id;


            fixtureCounter =
                Math.max(
                    fixtureCounter,
                    fixture.id
                );


            // Rotation

            fixture.group.rotation.set(

                data.rotation?.x ?? 0,

                data.rotation?.y ?? 0,

                data.rotation?.z ?? 0

            );


            // Pan / Tilt

            fixture.pan =
                data.pan ?? 0;

            fixture.tilt =
                data.tilt ?? 0;


            // Licht

            fixture.color =
                data.color ?? "#ffffff";

            fixture.intensity =
                data.intensity ?? 5;

            fixture.angle =
                data.angle ?? 20;


            fixture.devices =
                JSON.parse(
                    JSON.stringify(
                        data.devices ?? []
                    )
                );


            fixture.update();


            fixtures.push(
                fixture
            );

        }
    );


    // ----------------------------------------
    // UI
    // ----------------------------------------

    updateFixtureList();

    renderDeviceAssignments();


    // ----------------------------------------
    // AUSWAHL WIEDERHERSTELLEN
    // ----------------------------------------

    if (
        snapshot.selectedId !== null
    ) {

        const fixture =
            fixtures.find(
                item =>
                    item.id ===
                    snapshot.selectedId
            );


        if (fixture) {

            selectFixture(
                fixture
            );

        } else {

            clearPositionInputs();

        }

    } else {

        clearPositionInputs();

    }


    updateControls();


    projectChanged =
        true;
}


// ============================================================
// UNDO
// ============================================================

function undo() {

    endUndoAction();


    if (
        undoStack.length === 0
    ) {

        console.log(
            "Keine Undo-Schritte vorhanden."
        );

        return;
    }


    // aktuellen Zustand für REDO speichern

    redoStack.push(
        createHistorySnapshot()
    );


    if (
        redoStack.length >
        MAX_UNDO_STEPS
    ) {

        redoStack.shift();

    }


    const snapshot =
        undoStack.pop();


    restoreHistorySnapshot(
        snapshot
    );


    console.log(
        `Undo: noch ${undoStack.length} Schritte`
    );
}


// ============================================================
// REDO
// ============================================================

function redo() {

    endUndoAction();


    if (
        redoStack.length === 0
    ) {

        console.log(
            "Keine Redo-Schritte vorhanden."
        );

        return;
    }


    undoStack.push(
        createHistorySnapshot()
    );


    if (
        undoStack.length >
        MAX_UNDO_STEPS
    ) {

        undoStack.shift();

    }


    const snapshot =
        redoStack.pop();


    restoreHistorySnapshot(
        snapshot
    );


    console.log(
        `Redo: noch ${redoStack.length} Schritte`
    );
}


// ============================================================
// FIXTURE HINZUFÜGEN
// ============================================================

function addFixture(
    position = new THREE.Vector3()
) {

    beginUndoAction();


    fixtureCounter++;


    const fixture =
        new MovingHead(

            fixtureCounter,

            position

        );


    fixtures.push(
        fixture
    );


    selectFixture(
        fixture
    );


    updateFixtureList();

    markProjectChanged();

    endUndoAction();
}


// ============================================================
// SETTINGS KOPIEREN
// ============================================================

document.getElementById(
    "copySettings"
).addEventListener(

    "click",

    () => {

        if (!selectedFixture) {

            alert(
                "Please select a Moving Head first."
            );

            return;
        }


        copiedSettings = {

            pan:
                selectedFixture.pan,

            tilt:
                selectedFixture.tilt,

            color:
                selectedFixture.color,

            intensity:
                selectedFixture.intensity,

            angle:
                selectedFixture.angle

        };


        alert(
            "Settings copied."
        );

    }

);


// ============================================================
// SETTINGS EINFÜGEN
// ============================================================

document.getElementById(
    "pasteSettings"
).addEventListener(

    "click",

    () => {

        if (!selectedFixture) {

            alert(
                "Please select a Moving Head first."
            );

            return;
        }


        if (!copiedSettings) {

            alert(
                "No settings copied yet."
            );

            return;
        }


        beginUndoAction();


        selectedFixture.pan =
            copiedSettings.pan;

        selectedFixture.tilt =
            copiedSettings.tilt;

        selectedFixture.color =
            copiedSettings.color;

        selectedFixture.intensity =
            copiedSettings.intensity;

        selectedFixture.angle =
            copiedSettings.angle;


        selectedFixture.update();

        updateControls();

        markProjectChanged();

        endUndoAction();


        alert(
            "Settings pasted."
        );

    }

);


// ============================================================
// FIXTURE LÖSCHEN
// ============================================================


function deleteSelectedFixture() {
    if (!selectedFixture && !selectedTruss) return;

    beginUndoAction();

    if (selectedFixture) {
        const fixture = selectedFixture;

        fixture.setSelected(false);
        fixture.remove();

        fixtures = fixtures.filter(item => item !== fixture);
        selectedFixture = null;
    } else if (selectedTruss) {
        const truss = selectedTruss;

        truss.remove();

        trusses = trusses.filter(item => item !== truss);
        selectedTruss = null;
    }

    transformControls.detach();

    updateFixtureList();
    clearPositionInputs();
    renderDeviceAssignments();

    markProjectChanged();
    endUndoAction();
}



function selectFixture(fixture) {
    if (selectedFixture === fixture && !selectedTruss) return;

    if (selectedFixture) {
        selectedFixture.setSelected(false);
    }

    selectedTruss = null;
    selectedFixture = fixture;

    if (selectedFixture) {
        selectedFixture.setSelected(true);
        transformControls.attach(selectedFixture.group);
    } else {
        transformControls.detach();
    }

    updateFixtureList();
    updateControls();
    renderDeviceAssignments();
}

function selectTruss(truss) {
    if (selectedTruss === truss && !selectedFixture) return;

    if (selectedFixture) {
        selectedFixture.setSelected(false);
    }

    selectedFixture = null;
    selectedTruss = truss;

    transformControls.attach(truss.group);
    transformControls.setMode("translate");

    updateFixtureList();
    clearPositionInputs();
    renderDeviceAssignments();
}

function deselectFixture() {
    if (!selectedFixture && !selectedTruss) return;

    if (selectedFixture) {
        selectedFixture.setSelected(false);
    }

    selectedFixture = null;
    selectedTruss = null;

    transformControls.detach();

    updateFixtureList();
    clearPositionInputs();
    renderDeviceAssignments();
}


// ============================================================
// FIXTURE-LISTE
// ============================================================

function updateFixtureList() {
    const list = document.getElementById("fixtureList");
    list.innerHTML = "";

    // Moving Heads anzeigen
    fixtures.forEach(fixture => {
        const item = document.createElement("div");
        item.className = "fixture";

        if (selectedFixture === fixture) {
            item.classList.add("selected");
        }

        item.textContent = `Moving Head ${fixture.id}`;

        item.addEventListener("click", () => {
            selectFixture(fixture);
        });

        list.appendChild(item);
    });

    // Traversen anzeigen
    trusses.forEach(truss => {
        const item = document.createElement("div");
        item.className = "fixture";

        if (selectedTruss === truss) {
            item.classList.add("selected");
        }

        item.textContent = `Truss ${truss.id}`;

        item.addEventListener("click", () => {
            selectTruss(truss);
        });

        list.appendChild(item);
    });
}



function updateFixturePosition() {
    const object = selectedTruss || selectedFixture;

    if (!object) return;

    const snapPosition = value => Math.round(value / 0.1) * 0.1;

    const x = parseFloat(xInput.value);
    const y = parseFloat(yInput.value);
    const z = parseFloat(zInput.value);

    if (!Number.isNaN(x)) {
        object.group.position.x = snapPosition(x);
    }

    if (!Number.isNaN(y)) {
        object.group.position.y = snapPosition(y);
    }

    if (!Number.isNaN(z)) {
        object.group.position.z = snapPosition(z);
    }

    updateControls();
    markProjectChanged();
}

// ============================================================
// UI AKTUALISIEREN
// ============================================================

function updateControls() {
    // Kein Objekt ausgewählt
    if (!selectedFixture && !selectedTruss) {
        clearPositionInputs();
        return;
    }

    // Ausgewähltes Objekt bestimmen
    const object = selectedTruss
        ? selectedTruss
        : selectedFixture;

    // Position für beide Objekttypen anzeigen
    if (xInput) {
        xInput.value = object.group.position.x.toFixed(2);
    }

    if (yInput) {
        yInput.value = object.group.position.y.toFixed(2);
    }

    if (zInput) {
        zInput.value = object.group.position.z.toFixed(2);
    }

    // DMX-Regler nur bei Moving Heads aktualisieren
    if (!selectedFixture) {
        return;
    }

    const fixture = selectedFixture;

    document.getElementById("pan").value = fixture.pan;
    document.getElementById("panValue").textContent = `${fixture.pan}°`;

    document.getElementById("tilt").value = fixture.tilt;
    document.getElementById("tiltValue").textContent = `${fixture.tilt}°`;

    document.getElementById("color").value = fixture.color;

    document.getElementById("intensity").value = fixture.intensity;
    document.getElementById("intensityValue").textContent = fixture.intensity;

    document.getElementById("beamAngle").value = fixture.angle;
    document.getElementById("angleValue").textContent = `${fixture.angle}°`;
}



// ============================================================
// X / Y / Z INPUTS
// ============================================================

if (xInput) {

    xInput.addEventListener(
        "focus",
        () => {
            beginUndoAction();
        }
    );

    xInput.addEventListener(
        "blur",
        () => {
            endUndoAction();
        }
    );

    xInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


if (yInput) {

    yInput.addEventListener(
        "focus",
        () => {
            beginUndoAction();
        }
    );

    yInput.addEventListener(
        "blur",
        () => {
            endUndoAction();
        }
    );

    yInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


if (zInput) {

    zInput.addEventListener(
        "focus",
        () => {
            beginUndoAction();
        }
    );

    zInput.addEventListener(
        "blur",
        () => {
            endUndoAction();
        }
    );

    zInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


// ============================================================
// PAN
// ============================================================

const panInput =
    document.getElementById("pan");

panInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

panInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

panInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

panInput.addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.pan =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "panValue"
        ).textContent =
            `${selectedFixture.pan}°`;

    }
);


// ============================================================
// TILT
// ============================================================

const tiltInput =
    document.getElementById("tilt");

tiltInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

tiltInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

tiltInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

tiltInput.addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.tilt =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "tiltValue"
        ).textContent =
            `${selectedFixture.tilt}°`;

    }
);


// ============================================================
// FARBE
// ============================================================

const colorInput =
    document.getElementById("color");

colorInput.addEventListener(
    "focus",
    () => {
        beginUndoAction();
    }
);

colorInput.addEventListener(
    "blur",
    () => {
        endUndoAction();
    }
);

colorInput.addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.color =
            event.target.value;


        selectedFixture.update();

        markProjectChanged();

    }
);


// ============================================================
// INTENSITÄT
// ============================================================

const intensityInput =
    document.getElementById("intensity");

intensityInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

intensityInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

intensityInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

intensityInput.addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.intensity =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "intensityValue"
        ).textContent =
            selectedFixture.intensity;

    }
);


// ============================================================
// BEAM ANGLE
// ============================================================

const beamAngleInput =
    document.getElementById("beamAngle");

beamAngleInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

beamAngleInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

beamAngleInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

beamAngleInput.addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.angle =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "angleValue"
        ).textContent =
            `${selectedFixture.angle}°`;

    }
);


// ============================================================
// GLOBAL BEAM LÄNGE
// ============================================================

const globalBeamLengthInput =
    document.getElementById(
        "globalBeamLength"
    );

globalBeamLengthInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

globalBeamLengthInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

globalBeamLengthInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

globalBeamLengthInput.addEventListener(

    "input",

    event => {

        globalBeamLength =
            parseFloat(
                event.target.value
            );


        markProjectChanged();


        document.getElementById(
            "globalBeamLengthValue"
        ).textContent =
            `${globalBeamLength} m`;


        fixtures.forEach(
            fixture => {

                fixture.update();

            }
        );

    }
);


// ============================================================
// GLOBAL BEAM SICHTBARKEIT
// ============================================================

document.getElementById(
    "globalBeamToggle"
).addEventListener(

    "click",

    () => {

        beginUndoAction();


        globalBeamsVisible =
            !globalBeamsVisible;


        markProjectChanged();


        document.getElementById(
            "globalBeamToggle"
        ).textContent =
            globalBeamsVisible
                ? "Beam ON"
                : "Beam OFF";


        fixtures.forEach(
            fixture => {

                fixture.update();

            }
        );


        endUndoAction();

    }
);


// ============================================================
// UNIVERSUM GRÖSSE
// ============================================================

const universeSizeInput =
    document.getElementById(
        "universeSize"
    );

universeSizeInput.addEventListener(
    "pointerdown",
    () => {
        beginUndoAction();
    }
);

universeSizeInput.addEventListener(
    "pointerup",
    () => {
        endUndoAction();
    }
);

universeSizeInput.addEventListener(
    "change",
    () => {
        endUndoAction();
    }
);

universeSizeInput.addEventListener(

    "input",

    event => {

        const size =
            parseFloat(
                event.target.value
            );


        markProjectChanged();


        document.getElementById(
            "universeSizeValue"
        ).textContent =
            `${size} m`;


        updateUniverseSize(
            size
        );

    }
);


// ============================================================
// MOVING HEAD HINZUFÜGEN
// ============================================================

document.getElementById(
    "addFixture"
).addEventListener(

    "click",

    () => {

        const offset =
            fixtures.length * 1.5;


        addFixture(

            new THREE.Vector3(

                offset,
                0,
                0

            )

        );

    }
);


// ============================================================
// MOVING HEAD LÖSCHEN
// ============================================================

document.getElementById(
    "deleteFixture"
).addEventListener(

    "click",

    () => {

        deleteSelectedFixture();

    }
);

// ============================================================
// Traverse hinzufügen
// ============================================================


addTrussButton.addEventListener("click", () => {
    beginUndoAction();

    const truss = new Truss(
        new THREE.Vector3(0, 2, 0),
        2
    );

    trusses.push(truss);
    selectTruss(truss);

    markProjectChanged();
    endUndoAction();
});


// ============================================================
// HINT BUTTONS
// ============================================================

document.getElementById(
    "hintTranslate"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            transformControls.setMode(
                "translate"
            );

        }

    }
);


document.getElementById(
    "hintScale"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedTruss) {

            transformControls.setMode(
                "scale"
            );

        }

    }
);

document.getElementById(
    "hintDeselect"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            deselectFixture();

        }

    }
);


document.getElementById(
    "hintRotate"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            transformControls.setMode(
                "rotate"
            );

        }

    }
);


// ============================================================
// TRANSFORM MODUS
// ============================================================

window.addEventListener(

    "keydown",

    event => {

        // Tastenkürzel in Eingabefeldern ignorieren
        const target = event.target;
        const tag = target.tagName;

        if (
            !event.ctrlKey &&
            (
                tag === "INPUT" ||
                tag === "TEXTAREA" ||
                tag === "SELECT" ||
                target.isContentEditable
            )
        ) {
            return;
        }

        // ----------------------------------------
        // CTRL + S
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.key.toLowerCase() === "s"
        ) {

            event.preventDefault();

            saveProject();

            return;

        }


        // ----------------------------------------
        // CTRL + Z = UNDO
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.key.toLowerCase() === "z" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            undo();

            return;

        }


        // ----------------------------------------
        // CTRL + Y = REDO
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.key.toLowerCase() === "y"
        ) {

            event.preventDefault();

            redo();

            return;

        }


        // ----------------------------------------
        // CTRL + SHIFT + Z = REDO
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.shiftKey &&
            event.key.toLowerCase() === "z"
        ) {

            event.preventDefault();

            redo();

            return;

        }


        // ----------------------------------------
        // R = ROTATION
        // ----------------------------------------

        if (event.key.toLowerCase() === "r") {
            if (selectedFixture || selectedTruss) {
                if (selectTruss) {transformControls.attach(selectedTruss.group);
                transformControls.setSpace("world");
                transformControls.showX = true;
                transformControls.showY = true;
                transformControls.showZ = true;}                

                transformControls.setMode("rotate");
            }
        }


        // ----------------------------------------
        // G = POSITION
        // ----------------------------------------

        if (event.key.toLowerCase() === "g") {
            if (selectedFixture || selectedTruss) {
                
                transformControls.attach(selectedTruss.group);
                transformControls.setSpace("world");
                transformControls.showX = true;
                transformControls.showY = true;
                transformControls.showZ = true;

                transformControls.setMode("translate");
            }
        }

        
        // ----------------------------------------
        // T = SKALIEREN
        // ----------------------------------------

                
        if (event.key.toLowerCase() === "t") {
            if (selectedTruss) {
                transformControls.attach(selectedTruss.endHandle);
                transformControls.setMode("translate");
                transformControls.setSpace("local");

                transformControls.showX = true;
                transformControls.showY = false;
                transformControls.showZ = false;

                transformControls.setTranslationSnap(0.5);
            }
        }


        // ----------------------------------------
        // S = DESELECT
        // ----------------------------------------

        if (event.key.toLowerCase() === "s") {
            if (selectedFixture || selectedTruss) {
                deselectFixture();
            }
        }


        // ----------------------------------------
        // DELETE
        // ----------------------------------------

        /*
        if (
            event.key === "Delete"
        ) {

            deleteSelectedFixture();

        }
        */

    }
);


// ============================================================
// TRANSFORM ÄNDERUNGEN
// ============================================================

transformControls.addEventListener(

    "change",

    () => {

        if (!selectedFixture) {
            return;
        }


        updateControls();

        markProjectChanged();

    }
);



transformControls.addEventListener("objectChange", () => {
    if (!selectedTruss) return;

    if (transformControls.object === selectedTruss.endHandle) {
        const handle = selectedTruss.endHandle;
        const newLength = Math.max(0.5, handle.position.x);

        selectedTruss.setLength(newLength);

        markProjectChanged();
    }
});




// ============================================================
// 3D-MOUSE-PICKING
// ============================================================

const raycaster =
    new THREE.Raycaster();


const mouse =
    new THREE.Vector2();


// ============================================================
// POSITION AUF BODEN BESTIMMEN
// ============================================================

const groundPlane =
    new THREE.Plane(

        new THREE.Vector3(
            0,
            1,
            0
        ),

        0

    );


const intersectionPoint =
    new THREE.Vector3();



// ============================================================
// MOUSE CLICK
// ============================================================

renderer.domElement.addEventListener(

    "pointerdown",

    event => {

        if (
            event.button !== 0
        ) {

            return;

        }


        if (
            transformControls.dragging
        ) {

            return;

        }


        const rect =
            renderer.domElement
                .getBoundingClientRect();


        mouse.x =
            (

                (event.clientX - rect.left) /
                rect.width

            ) * 2 - 1;


        mouse.y =
            -(

                (event.clientY - rect.top) /
                rect.height

            ) * 2 + 1;


        raycaster.setFromCamera(
            mouse,
            camera
        );


        // ----------------------------------------
        // FIXTURE SUCHEN
        // ----------------------------------------

        const objects = [];


        fixtures.forEach(

            fixture => {

                fixture.group.traverse(

                    object => {

                        if (
                            object.isMesh
                        ) {

                            objects.push(
                                object
                            );

                        }

                    }

                );

            }

        );


        const intersections =
            raycaster.intersectObjects(

                objects,

                true

            );


        // ----------------------------------------
        // FIXTURE GETROFFEN
        // ----------------------------------------

        if (
            intersections.length > 0
        ) {

            const clickedObject =
                intersections[0].object;


            let parent =
                clickedObject;


            while (

                parent &&

                !fixtures.some(

                    fixture =>
                        fixture.group === parent

                )

            ) {

                parent =
                    parent.parent;

            }


            if (parent) {

                const fixture =
                    fixtures.find(

                        fixture =>
                            fixture.group === parent

                    );


                if (fixture) {

                    selectFixture(
                        fixture
                    );


                    return;

                }

            }

        }


        // ----------------------------------------
        // SHIFT + CLICK
        // ----------------------------------------

        if (
            event.shiftKey &&
            selectedFixture
        ) {

            beginUndoAction();


            if (
                raycaster.ray.intersectPlane(

                    groundPlane,

                    intersectionPoint

                )
            ) {

                selectedFixture.group.position.x =
                    intersectionPoint.x;


                selectedFixture.group.position.z =
                    intersectionPoint.z;


                updateControls();

                markProjectChanged();

            }


            endUndoAction();

            return;

        }


        // ----------------------------------------
        // KLICK DANEBEN
        // ----------------------------------------

        // deselectFixture();

    }
);



// ============================================================
// PROJEKT ALS JSON ERSTELLEN
// ============================================================

function getProjectData() {

    return {

        universeSize:
            universeSize,

        globalBeamLength:
            globalBeamLength,

        globalBeamsVisible:
            globalBeamsVisible,

        fixtures:
            fixtures.map(
                fixture => ({

                    id:
                        fixture.id,

                    position: {

                        x:
                            fixture.group.position.x,

                        y:
                            fixture.group.position.y,

                        z:
                            fixture.group.position.z

                    },

                    rotation: {

                        x:
                            fixture.group.rotation.x,

                        y:
                            fixture.group.rotation.y,

                        z:
                            fixture.group.rotation.z

                    },

                    pan:
                        fixture.pan,

                    tilt:
                        fixture.tilt,

                    color:
                        fixture.color,

                    intensity:
                        fixture.intensity,

                    angle:
                        fixture.angle,

                    devices:
                        fixture.devices

                })
            ),
        stageObjects: stageObjects.map(object => ({
            id: object.id,
            type: object.type,
            position: {
                x: object.group.position.x,
                y: object.group.position.y,
                z: object.group.position.z
            },
            rotation: {
                x: object.group.rotation.x,
                y: object.group.rotation.y,
                z: object.group.rotation.z
            },
            width: object.width,
            height: object.height,
            depth: object.depth
        })),

        trusses: trusses.map(truss => ({
            id: truss.id,
            length: truss.length,
            position: {
                x: truss.group.position.x,
                y: truss.group.position.y,
                z: truss.group.position.z
            },
            rotation: {
                x: truss.group.rotation.x,
                y: truss.group.rotation.y,
                z: truss.group.rotation.z
            }
        }))

    };
}


// ============================================================
// PROJEKT SPEICHERN
// ============================================================

document.getElementById(
    "saveProject"
).addEventListener(

    "click",

    () => {

        saveProject();

    }

);


// ============================================================
// PROJEKT SPEICHERN
// ============================================================

async function saveProject() {

    const project =
        getProjectData();


    const saveButton =
        document.getElementById(
            "saveProject"
        );


    try {

        const response =
            await fetch(

                "/api/project/save",

                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            project
                        )

                }

            );


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(

                result.error ||
                "Unbekannter Fehler"

            );

        }


        console.log(
            "Projekt gespeichert."
        );


        projectChanged =
            false;


        saveButton.textContent =
            "✓";


        setTimeout(

            () => {

                saveButton.textContent =
                    "Save";

            },

            1500

        );


    } catch (error) {

        console.error(

            "Speichern fehlgeschlagen:",
            error

        );


        alert(
            "Projekt konnte nicht gespeichert werden."
        );

    }

}


// ============================================================
// PROJEKT BEIM START LADEN
// ============================================================

function loadInitialProject() {

    if (
        !initialProject ||
        !Array.isArray(initialProject.fixtures)
    ) {

        return;

    }


    // ----------------------------------------
    // UNIVERSUM
    // ----------------------------------------

    if (
        initialProject.universeSize !== undefined
    ) {

        universeSize =
            initialProject.universeSize;


        updateUniverseSize(
            universeSize
        );


        document.getElementById(
            "universeSize"
        ).value =
            universeSize;


        document.getElementById(
            "universeSizeValue"
        ).textContent =
            `${universeSize} m`;

    }


    // ----------------------------------------
    // GLOBALER BEAM
    // ----------------------------------------

    if (
        initialProject.globalBeamLength !== undefined
    ) {

        globalBeamLength =
            initialProject.globalBeamLength;


        document.getElementById(
            "globalBeamLength"
        ).value =
            globalBeamLength;


        document.getElementById(
            "globalBeamLengthValue"
        ).textContent =
            `${globalBeamLength} m`;

    }


    // ----------------------------------------
    // GLOBALER BEAM SICHTBARKEIT
    // ----------------------------------------

    if (
        initialProject.globalBeamsVisible !== undefined
    ) {

        globalBeamsVisible =
            initialProject.globalBeamsVisible;


        document.getElementById(
            "globalBeamToggle"
        ).textContent =
            globalBeamsVisible
                ? "Beam ON"
                : "Beam OFF";

    }


    // ----------------------------------------
    // FIXTURES
    // ----------------------------------------

    initialProject.fixtures.forEach(

        data => {

            const fixture =
                new MovingHead(

                    data.id,

                    new THREE.Vector3(

                        data.position?.x ?? 0,

                        data.position?.y ?? 0,

                        data.position?.z ?? 0

                    )

                );


            fixture.id =
                data.id;


            fixtureCounter =
                Math.max(

                    fixtureCounter,

                    fixture.id

                );


            // ----------------------------------------
            // ROTATION
            // ----------------------------------------

            fixture.group.rotation.set(

                data.rotation?.x ?? 0,

                data.rotation?.y ?? 0,

                data.rotation?.z ?? 0

            );


            // ----------------------------------------
            // PAN / TILT
            // ----------------------------------------

            fixture.pan =
                data.pan ?? 0;


            fixture.tilt =
                data.tilt ?? 0;


            // ----------------------------------------
            // LICHT
            // ----------------------------------------

            fixture.color =
                data.color ?? "#ffffff";


            fixture.intensity =
                data.intensity ?? 5;


            fixture.angle =
                data.angle ?? 20;

            fixture.devices =
                JSON.parse(
                    JSON.stringify(
                        data.devices ?? []
                    )
                );


            fixture.update();


            fixtures.push(
                fixture
            );

        }

    );
    
    // Traversen laden
    if (Array.isArray(initialProject.trusses)) {
        initialProject.trusses.forEach(data => {
            const position = data.position || { x: 0, y: 2, z: 0 };

            const truss = new Truss(
                new THREE.Vector3(
                    position.x,
                    position.y,
                    position.z
                ),
                data.length ?? 2
            );

            if (data.id) {
                truss.id = data.id;

                const number = parseInt(data.id.replace("TR", ""), 10);
                if (!Number.isNaN(number)) {
                    trussCounter = Math.max(trussCounter, number);
                }
            }

            if (data.rotation) {
                truss.group.rotation.set(
                    data.rotation.x ?? 0,
                    data.rotation.y ?? 0,
                    data.rotation.z ?? 0
                );
            }

            trusses.push(truss);
        });
    }


    updateFixtureList();


    if (fixtures.length > 0) {

        selectFixture(
            fixtures[0]
        );

    }


    projectChanged =
        false;
}


// ============================================================
// RESIZE
// ============================================================

window.addEventListener(

    "resize",

    () => {

        const width =
            sceneContainer.clientWidth;


        const height =
            sceneContainer.clientHeight;


        camera.aspect =
            width / height;


        camera.updateProjectionMatrix();


        renderer.setSize(

            width,

            height

        );

    }

);


// ============================================================
// PROJEKT GEÄNDERT
// ============================================================

function markProjectChanged() {

    projectChanged =
        true;


    const saveButton =
        document.getElementById(
            "saveProject"
        );


    if (saveButton) {

        saveButton.textContent =
            "*Save";

    }

}


// ============================================================
// RENDER LOOP
// ============================================================

function animate() {

    requestAnimationFrame(
        animate
    );


    controls.update();


    renderer.render(

        scene,

        camera

    );

}


animate();


// ============================================================
// START
// ============================================================

if (
    initialProject &&
    Array.isArray(initialProject.fixtures) &&
    initialProject.fixtures.length > 0
) {

    loadInitialProject();

} else {

    addFixture(

        new THREE.Vector3(

            0,
            0,
            0

        )

    );

}