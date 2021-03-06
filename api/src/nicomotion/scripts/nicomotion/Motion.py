import logging
import json
import re
import pprint

import pypot.robot
import pypot.vrep

import _nicomotion_internal.hand


class Motion:
    """
    The Motion class provides a high level interface to various movement related functions of the NICO robot
    """

    def __init__(self, motorConfig='config.json', vrep=False, vrepHost='127.0.0.1', vrepPort=19997, vrepScene=None):
        """
        Motion is an interface to control the movement of the NICO robot.

        :param motorConfig: motor config file (JSON format)
        :type motorConfig: str
        :param vrep: If set to true VREP will be used instead of real robot
        :type vrep: bool
        :param vrepHost: Network address of VREP
        :type vrepHost: str
        :param vrepPort: Port of VREP
        :type vrepPort: int
        :param vrepScene: Scene to load. Set to None to use current scene
        :type vrepScene: str
        """
        self._robot = None
        self._maximumSpeed = 1.0
        self._vrep = vrep

        with open(motorConfig, 'r') as config_file:
            config = json.load(config_file)

        if vrep:
            logging.info('Using VREP')
            # TODO Remove the filtering of l_wrist_x once the new model is updated
            to_remove = ['l_virtualhand_x', 'r_virtualhand_x', 'l_wrist_x', 'r_wrist_x']
            for motor in to_remove:
                config['motors'].pop(motor)
                for group in config['motorgroups'].keys():
                    config['motorgroups'][group] = [x for x in config['motorgroups'][group] if x != motor]
            self._robot = pypot.vrep.from_vrep(config, vrepHost, vrepPort, vrepScene)
        else:
            logging.info('Using robot')
            try:
                self._robot = pypot.robot.from_config(config)
            except IndexError as e:
                regex = re.compile('.*\[.*\].*\[(?P<ids>.*)\].*')
                match = regex.match(e.message)
                string = match.group('ids')
                for id in string.split(','):
                    id = int(id)
                    for motor in config['motors'].keys():
                        if config['motors'][motor]['id'] == id:
                            logging.warning('Removing motor %s (%i)' %(motor, id))
                            config['motors'].pop(motor)
                            for group in config['motorgroups'].keys():
                                config['motorgroups'][group] = [x for x in config['motorgroups'][group] if x != motor]
                logging.warning('New config created:')
                logging.warning(pprint.pformat(config))
                self._robot = pypot.robot.from_config(config)



    def openHand(self, handName, fractionMaxSpeed=1.0, percentage=1.0):
        """
        Opens the specified hand. handName can be 'RHand' or 'LHand'

        :param handName: Name of the hand (RHand, LHand)
        :type handName: str
        :param fractionMaxSpeed: Speed at which hand should open. Default: 1.0
        :type fractionMaxSpeed: float
        :param percentage: Percentage hand should open. 0.0 < percentage <= 1.0
        :type percentage: float
        """
        if self._vrep:
            _nicomotion_internal.hand.openHandVREP(self._robot, handName, min(fractionMaxSpeed, self._maximumSpeed), percentage)
        else:
            _nicomotion_internal.hand.openHand(self._robot, handName, min(fractionMaxSpeed, self._maximumSpeed), percentage)

    def closeHand(self, handName, fractionMaxSpeed=1.0, percentage=1.0):
        """
        Closes the specified hand. handName can be 'RHand' or 'LHand'

        :param handName: Name of the hand (RHand, LHand)
        :type handName: str
        :param fractionMaxSpeed: Speed at which hand should close. Default: 1.0
        :type fractionMaxSpeed: float
        :param percentage: Percentage hand should open. 0.0 < percentage <= 1.0
        :type percentage: float
        """
        if self._vrep:
            _nicomotion_internal.hand.closeHandVREP(self._robot, handName, min(fractionMaxSpeed, self._maximumSpeed), percentage)
        else:
            _nicomotion_internal.hand.closeHand(self._robot, handName, min(fractionMaxSpeed, self._maximumSpeed), percentage)

    def enableForceControlAll(self, goalForce = 500):
        """
        Enables force control for all joints which support this feature

        :param goalForce: Goal force (0-2000)
        :type goalForce: int
        """
        for motor in self._robot.motors:
            if hasattr(motor, 'force_control_enable'):
                motor.force_control_enable = True
                motor.goal_force = goalForce

    def disableForceControlAll(self):
        """
        Disables force control for all joints which support this feature
        """
        for motor in self._robot.motors:
            if hasattr(motor, 'force_control_enable'):
                motor.force_control_enable = False

    def enableForceControl(self, jointName, goalForce):
        """
        Enables force control for a single joint

        :param jointName: Name of the joint
        :type jointName: str
        :param goalForce: Goal force (0-2000)
        :type goalForce: int
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'force_control_enable'):
                motor.force_control_enable = True
                motor.goal_force = goalForce
            else:
                logging.warning('Joint %s has no force control' % jointName)
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def disableForceControl(self, jointName):
        """
        Disables force control for a single joint

        :param jointName: Name of the joint
        :type jointName: str
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'force_control_enable'):
                motor.force_control_enable = False
            else:
                logging.warning('Joint %s has no force control' % jointName)
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def setAngle(self, jointName, angle, fractionMaxSpeed):
        """
        Sets the angle of a given joint to an angle (in degree)

        :param jointName: Name of the joint
        :type jointName: str
        :param angle: Angle (in degree)
        :type angle: float
        :param fractionMaxSpeed: Movement speed of joint
        :type fractionMaxSpeed: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            motor.compliant = False
            motor.goal_speed = 1000.0 * min(fractionMaxSpeed, self._maximumSpeed)
            motor.goal_position = angle
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def changeAngle(self, jointName, change, fractionMaxSpeed):
        """
        Changes the angle of a given joint by an angle (in degree)

        :param jointName: Name of the joint
        :type jointName: str
        :param angle: Angle (in degree)
        :type angle: float
        :param fractionMaxSpeed: Movement speed of joint
        :type fractionMaxSpeed: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            motor.compliant = False
            motor.goal_speed = 1000.0 * min(fractionMaxSpeed, self._maximumSpeed)
            motor.goal_position = change + motor.present_position
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def getAngle(self, jointName):
        """
        Returns the current angle of a given joint (in degree)

        :param jointName: Name of the joint
        :type jointName: str
        :return: Angle of the joint (degree)
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            return motor.present_position
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def getJointNames(self):
        """
        Returns all joint names

        :return: List with joint names
        :rtype: list
        """
        jointNames = []
        for motor in self._robot.motors:
            jointNames += [motor.name]
        return jointNames

    def getSensorNames(self):
        """
        Returns all sensor names

        :return: List with sensor names
        :rtype: list
        """
        sensorNames = []
        for sensor in self._robot.sensors:
            sensorNames += [sensor.name]
        return sensorNames

    def getAngleUpperLimit(self, jointName):
        """
        Returns the upper angle limit of a joint (in degree)

        :param jointName: Name of the joint
        :type jointName: str
        :return: Upper angle limit of the joint (degree)
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            return motor.upper_limit
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def getAngleLowerLimit(self, jointName):
        """
        Returns the lower angle limit of a joint (in degree)

        :param jointName: Name of the joint
        :type jointName: str
        :return: Lower angle limit of the joint (degree)
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            return motor.lower_limit
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def getTorqueLimit(self, jointName):
        """
        Returns the torque limit of a joint

        :param jointName: Name of the joint
        :type jointName: str
        :return: Torque limit of the joint
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            return motor.torque_limit
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def getTemperature(self, jointName):
        """
        Returns the current temperature of a motor

        :param jointName: Name of the joint
        :type jointName: str
        :return: Temperature of the joint
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'present_temperature'):
                return motor.present_temperature
            else:
                logging.warning('Joint %s has no present temperature' % jointName)
                return 0.0
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def getCurrent(self, jointName):
        """
        Returns the current current of a motor

        :param jointName: Name of the joint
        :type jointName: str
        :return: Current of the joint
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'present_current'):
                return motor.present_current
            else:
                logging.warning('Joint %s has no present current' % jointName)
                return 0.0
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def setMaximumSpeed(self, maximumSpeed):
        """
        Sets the maximum allowed speed (in fraction of maximum possible speed). When giving a higher speed to any other
        functions the movement won't go over the value set here

        :param maximumSpeed: Maximum allowed speed (0 <= maximumSpeed <= 1.0)
        """
        if not 0.0 <= maximumSpeed <= 1.0:
            logging.warning('New maximum speed out of bounds (%d)' % maximumSpeed)
            return
        self._maximumSpeed = maximumSpeed

    def setStiffness(self, jointName, stiffness):
        """
        Sets the stiffness (0 <= stiffness <= 1) for a single motor

        :param jointName: Name of the joint
        :type jointName: str
        :param stiffness: Target stiffness
        :type stiffness: float
        """
        if not 0.0 <= stiffness <= 1.0:
            logging.warning('New stiffness out of bounds (%d)' % maximumSpeed)
            return

        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'torque_limit'):
                motor.torque_limit = 100.0 * stiffness
            else:
                logging.warning('Joint %s has no torque limit' % jointName)

            if(stiffness < 0.001):
                self.disableTorque(jointName)
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def getStiffness(self, jointName):
        """
        Returns the current stiffness of a motor

        :param jointName: Name of the joint
        :type jointName: str
        :return: Stiffness of the joint
        :rtype: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if motor.compliant: # no torque
                return 0.0
            elif hasattr(motor, 'torque_limit'):
                return motor.torque_limit / 100.0
            else:
                logging.warning('Joint %s has no torque limit' % jointName)
                return 1.0
        else:
            logging.warning('No joint "%s" found' % jointName)
            return 0.0

    def setPID(self, jointName, p, i, d):
        """
        Sets the PID controller for a single motor. For more information see
        http://support.robotis.com/en/product/actuator/dynamixel/mx_series/mx-64at_ar.htm#Actuator_Address_1A

        :param jointName: Name of the joint
        :type jointName: str
        :param p: Proportional band
        :type p: float
        :param i: Integral action
        :type i: float
        :param d: Derivative action
        :type d: float
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'pid'):
                motor.pid = (p, i, d)
            else:
                logging.warning('Joint %s has no pid' % jointName)
        else:
            logging.warning('No joint "%s" found' % jointName)
            return

    def getPID(self, jointName):
        """
        Returns the current stifftness of a motor. For more information see
        http://support.robotis.com/en/product/actuator/dynamixel/mx_series/mx-64at_ar.htm#Actuator_Address_1A

        :param jointName: Name of the joint
        :type jointName: str
        :return: Tupel: p,i,d
        :rtype: tuple
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            if hasattr(motor, 'pid'):
                return motor.pid
            else:
                logging.warning('Joint %s has no pid' % jointName)
                return (0.0, 0.0, 0.0)
        else:
            logging.warning('No joint "%s" found' % jointName)
            return (0.0, 0.0, 0.0)

    def enableTorqueAll(self):
        """
        Enables toruqe on all joints
        """
        for motor in self._robot.motors:
            motor.compliant = False

    def disableTorqueAll(self):
        """
        Disables toruqe on all joints
        """
        for motor in self._robot.motors:
            motor.compliant = True

    def enableTorque(self, jointName):
        """
        Enables torque on a single joint.

        :param jointName: Name of the motor
        :type jointName: str
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            motor.compliant = False
        else:
            logging.warning('No joint "%s" found' % jointName)

    def disableTorque(self, jointName):
        """
        Disables torque on a single joint.

        :param jointName: Name of the motor
        :type jointName: str
        """
        if hasattr(self._robot, jointName):
            motor = getattr(self._robot, jointName)
            motor.compliant = True
        else:
            logging.warning('No joint "%s" found' % jointName)

    def cleanup(self):
        """
        Cleans up the current connection to the robot. After this you can no longer control the robot
        """
        if self._robot is None:
            logging.warning('Cleanup called - but robot is not initialised')
            return

        logging.info('Closing robot connection')
        self._robot.close()
        self._robot = None
        logging.shutdown()

    def __del__(self):
        """
        Destructor
        """
        if self._robot is  not None:
            self.cleanup()
